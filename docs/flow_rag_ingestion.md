# RAG Ingestion Pipeline — Explicación de Pasos

> Documento complementario al diagrama `flow_rag_ingestion.excalidraw`.  
> Archivo fuente: `ingestion/pipeline.py`

---

## Introducción

El pipeline de ingestión es el componente responsable de mantener el **vector store (PGVector)** sincronizado con el catálogo de productos de la base de datos PostgreSQL. Funciona en modo **incremental**: sólo procesa los cambios (nuevos, modificados o eliminados) en lugar de re-indexar todo en cada ejecución, lo que minimiza costes de embedding y escrituras innecesarias.

### Modos de ejecución

| Modo | Llamada | Descripción |
|------|---------|-------------|
| **Incremental** (por defecto) | `run_pipeline()` | Sólo procesa cambios respecto al último estado indexado |
| **Forzado** | `run_pipeline(force=True)` | Re-indexa todos los productos activos, ignorando el estado de sync |
| **Producto único** | `run_pipeline(product_id=5)` | Sincroniza un único producto (útil para eventos webhook) |

---

## Ciclo de Vida y Ejecución (Docker)

El repositorio está diseñado para funcionar de forma autónoma o como un servicio reactivo dentro de un contenedor Docker.

### 1. El Proceso de Arranque
Cuando ejecutas `docker-compose up` o lanzas el contenedor, el flujo técnico es el siguiente:
1. **Dockerfile**: El contenedor se construye basándose en una imagen de Python 3.11. Instala las dependencias necesarias para conectar con PostgreSQL y ejecutar el pipeline.
2. **Punto de Entrada**: La última instrucción del Dockerfile es `CMD ["python", "-m", "ingestion.main"]`. Esto ejecuta el script principal [main.py](file:///c:/Users/jlsan/Documents/Proyectos%20Programacion/whatsapp-commerce/whatsapp-commerce-rag-ingestion/ingestion/main.py).
3. **Carga de Configuración**: [main.py](file:///c:/Users/jlsan/Documents/Proyectos%20Programacion/whatsapp-commerce/whatsapp-commerce-rag-ingestion/ingestion/main.py) lee el archivo `.env` mediante [config.py](file:///c:/Users/jlsan/Documents/Proyectos%20Programacion/whatsapp-commerce/whatsapp-commerce-rag-ingestion/ingestion/config.py) para decidir cómo comportarse.

### 2. Modos de Ejecución (Diferentes a los tipos de sincronización)
Dependiendo de las variables en tu `.env`, el servicio puede operar de tres formas:

- **Modo One-Shot (Ejecución única)**: 
  - Si `SCHEDULE_INTERVAL_MINUTES=0` y `API_ENABLED=false`.
  - El pipeline se ejecuta una vez, sincroniza los cambios y el contenedor se detiene. Es ideal para tareas programadas (CronJobs).
- **Modo Scheduler (Planificador)**:
  - Si `SCHEDULE_INTERVAL_MINUTES` es mayor que 0 (ej: `60` para una hora).
  - El contenedor se mantiene vivo y repite el proceso de sincronización cíclicamente cada N minutos.
- **Modo API (Event-Driven)**:
  - Si `API_ENABLED=true`.
  - Se levanta un servidor FastAPI (puerto 8001 por defecto). Esto permite que el backend de la aplicación avise al pipeline para que re-indexe un producto específico inmediatamente después de que un administrador lo edite en el panel, sin esperar al siguiente ciclo del planificador.

---

## Pasos del Pipeline

### Paso 1 — Inicialización del engine y la sesión SQL

```python
engine = create_engine(settings.DATABASE_URL)
SQLModel.metadata.create_all(engine, tables=[IngestionSyncState.__table__])
```

- Se crea el engine de SQLAlchemy apuntando a la base de datos **PostgreSQL de la empresa**. 
  > [!NOTE]
  > Esta es la base de datos principal donde la empresa mantiene su catálogo de productos; es la fuente de verdad que el pipeline consulta para sincronizar la información.
- Se abre una sesión (`Session`).
- Se garantiza que la tabla `IngestionSyncState` existe (se crea si no existe). Esta tabla actúa como registro de qué productos ya están indexados y en qué versión.
- Se inicializa el diccionario `summary` con contadores: `added`, `updated`, `removed`, `skipped`, `errors`.

---

### Paso 2 — Fetch de productos activos desde PostgreSQL

```python
stmt = select(Product).where(Product.is_available == True)
if product_id is not None:
    stmt = stmt.where(Product.id == product_id)
active_products = session.exec(stmt).all()
```

- Se consultan todos los productos con `is_available = True`.
- Si se especificó `product_id`, el filtro se aplica sólo a ese producto.
- El resultado es la fuente de verdad sobre qué existe actualmente en el catálogo.

---

### Paso 3 — Decisión: ¿producto único inactivo?

```python
if not active_products and product_id is not None:
    await _delete_by_product_ids(vector_store, [product_id])
    _delete_sync_state(session, product_id)
    session.commit()
    return summary  # removed = 1
```

> **Caso especial del modo evento-driven.**

Si se pasó un `product_id` concreto pero no se encontró ningún producto activo con ese ID, significa que el producto fue **deshabilitado o eliminado**. En ese caso:

1. Se elimina su embedding del vector store.
2. Se elimina su entrada de `IngestionSyncState`.
3. Se hace commit y se retorna inmediatamente.

---

### Paso 4 — Decisión: ¿no hay productos activos?

```python
if not active_products:
    logger.warning("[pipeline] No active products found. Nothing to ingest.")
    return summary
```

- Si la consulta no devolvió ningún producto (sin filtro de `product_id`), el pipeline termina con un warning y retorna el summary vacío. No hay nada que indexar.

---

### Paso 5 — Carga del estado de sincronización

```python
sync_state = _load_sync_state(session) if not force else {}
```

- Se carga la tabla `IngestionSyncState` como un diccionario `{product_id: synced_version}`.
- Si el modo es `force=True`, el estado se ignora (diccionario vacío), forzando que todos los productos sean tratados como nuevos.

---

### Paso 6 — Cálculo del diff de 3 vías

```python
for product in active_products:
    if product.id not in sync_state:
        to_add.append(product)           # NEW
    elif force or product.version > sync_state[product.id]:
        to_update.append(product)        # CHANGED
    else:
        summary["skipped"] += 1          # UNCHANGED

removed_ids = [pid for pid in sync_state if pid not in active_ids]
```

Se clasifican todos los productos en 4 categorías:

| Categoría | Condición | Acción |
|-----------|-----------|--------|
| **NEW** | En SQL pero no en sync state | Embeder y añadir al VS |
| **CHANGED** | En SQL y en sync state, pero con versión mayor | Borrar embedding antiguo + re-embeder |
| **UNCHANGED** | En SQL y en sync state con la misma versión | Saltar (sin coste de embedding) |
| **REMOVED** | En sync state pero ya no en SQL activo | Borrar embedding + eliminar de sync state |

---

### Paso 7 — Decisión: ¿nada que sincronizar?

```python
if not to_add and not to_update and not ids_to_delete_from_vs:
    logger.info("[pipeline] Vector store is already up to date.")
    return summary
```

- Si el diff no genera ningún cambio (todo UNCHANGED), el pipeline termina aquí sin tocar el vector store. **Coste cero** en embeddings.

---

### Paso 8 — Inicialización del vector store

```python
embeddings = get_embeddings()
vector_store = _get_vector_store(embeddings)
```

- **Modelo de Embeddings (Inicialización Crítica)**: Se instancia el motor de IA que "traduce" el catálogo a lenguaje vectorial. 
  > [!IMPORTANT]
  > Se ha seleccionado el modelo **`text-embedding-3-small`** de OpenAI por tres razones clave:
  > 1. **Eficiencia de costes**: Es significativamente más barato que modelos anteriores manteniendo una precisión altísima.
  > 2. **Rendimiento Multilingüe**: Es excelente entendiendo descripciones de productos en español y otros idiomas, algo vital para el comercio por WhatsApp.
  > 3. **Consistencia**: Al ser un modelo de última generación, garantiza que las búsquedas semánticas del cliente sean mucho más precisas incluso si no usa las palabras exactas del nombre del producto.
  
  *Nota sobre Desarrollo Local:* En tu ordenador, el sistema usa **Ollama** con un modelo local (ej: `nomic-embed-text`). Esto permite hacer infinitas pruebas **sin costes de API ($0)**.

  > [!CAUTION]
  > **Incompatibilidad de Vectores**: Los vectores generados por Ollama NO son compatibles con los de OpenAI. Si cambias de local a producción (o viceversa), los vectores existentes en la base de datos no servirán. En ese caso, deberás ejecutar el pipeline con el flag `--force` para borrar y regenerar todos los embeddings desde cero con el nuevo modelo.

- **Conexión al Vector Store (PGVector)**: Se configura el almacén de vectores dentro de PostgreSQL. El sistema utiliza `settings.COLLECTION_NAME` para organizar los datos bajo una etiqueta específica; de este modo, el RAG sabrá exactamente de qué catálogo extraer la información durante una consulta real del cliente por WhatsApp.

---

### Paso 9 — Eliminación de embeddings obsoletos

```python
stale_ids = ids_to_delete_from_vs + [p.id for p in to_update]
await _delete_by_product_ids(vector_store, stale_ids)
```

- Se eliminan los embeddings correspondientes a:
  - Productos **REMOVED** (ya no existen o están desactivados).
  - Productos **CHANGED** (se eliminan los embeddings antiguos antes de re-indexar).
- Se usa `vector_store.adelete(filter={"product_id": pid})` para borrar por metadato.

---

### Paso 10 — Chunking, embedding y upsert

```python
docs = chunk_products(products_to_embed)
await vector_store.aadd_texts(
    texts=[d.text for d in docs],
    metadatas=[d.metadata for d in docs],
    ids=[d.doc_id for d in docs],
)
```

- Los productos `NEW + CHANGED` pasan por `chunk_products()` para convertirse en documentos con texto enriquecido y metadatos.
- Se utiliza una técnica de **Upsert** (Update + Insert) en PGVector basada en **IDs deterministas**:
  - **Generación de Embeddings**: En este punto, el sistema aplica el modelo de IA seleccionado: **OpenAI (`text-embedding-3-small`)** en producción, o **Ollama (`nomic-embed-text`)** en local. El modelo "escanea" el texto de cada producto y lo convierte en un vector numérico que captura su significado.
  - **IDs deterministas**: En lugar de asignar un ID aleatorio cada vez, el pipeline genera el `doc_id` basado en el ID del producto (ej: `prod-5`). Esto significa que un mismo producto siempre tendrá el mismo ID en el vector store.
  - **Idempotencia**: Gracias a estos IDs, si ejecutas el pipeline 10 veces seguidas, la base de datos no tendrá 10 copias del mismo producto. Simplemente "sobreescribirá" (update) la versión anterior con la nueva, asegurando que siempre haya una única versión válida por producto.
  - **Evita duplicados**: Esto es vital para que, si el proceso se interrumpe y se vuelve a lanzar, no terminemos con datos repetidos que ensucien los resultados de búsqueda del RAG.

---

### Paso 11 — Actualización del sync state y commit

```python
for p in products_to_embed:
    _update_sync_state(session, p.id, p.version)
for pid in ids_to_delete_from_vs:
    _delete_sync_state(session, pid)
session.commit()
```

- Se actualiza `IngestionSyncState` con la nueva versión de cada producto procesado.
- Se eliminan del sync state los productos que ya no están activos.
- Se hace commit de todos los cambios en una sola transacción.

---

### Paso 12 — (Opcional) Ingestión de StoreSetting

```python
if product_id is None and settings.INGEST_STORE_SETTINGS:
    await _ingest_store_settings(engine, embeddings, vector_store)
```

- Si la variable de entorno `INGEST_STORE_SETTINGS` está activa y no estamos en modo producto único, se indexan también las filas de `StoreSetting` (información de la tienda, FAQs, etc.).
- Esta operación es **idempotente** gracias a IDs deterministas del tipo `"setting-{key}"`.
- Si falla, sólo emite un warning (no interrumpe el pipeline).

---

### Paso 13 — Retorno del summary

```python
return summary
# Ejemplo: {"added": 3, "updated": 1, "removed": 0, "skipped": 12, "errors": 0}
```

- Se retorna un diccionario con los contadores finales para observabilidad (logs, respuestas de API).

---

## Helpers internos

| Función | Descripción |
|---------|-------------|
| `_get_vector_store(embeddings)` | Crea la instancia de PGVector con modo async |
| `_upsert_docs(vector_store, docs)` | Inserta/actualiza documentos usando IDs deterministas |
| `_delete_by_product_ids(vector_store, ids)` | Elimina embeddings filtrando por `metadata.product_id` |
| `_load_sync_state(session)` | Carga `{product_id: version}` desde la tabla de sync |
| `_update_sync_state(session, id, version)` | Upsert de la versión sincronizada de un producto |
| `_delete_sync_state(session, id)` | Elimina la entrada de un producto del sync state |
| `_ingest_store_settings(engine, emb, vs)` | Indexa filas de `StoreSetting` en el vector store |

---

## Diagrama de referencia

Ver [`flow_rag_ingestion.excalidraw`](./flow_rag_ingestion.excalidraw) para la representación visual del flujo completo.
