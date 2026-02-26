-- 02_seed.sql
-- Sample data for local development.
-- Runs after 01_schema.sql (PostgreSQL executes init scripts alphabetically).

INSERT INTO product (name, description, price, category, stock, is_available, version, updated_at)
VALUES
  ('Camiseta Básica Blanca', 'Camiseta de algodón 100% orgánico, corte regular, disponible en tallas S-XL.', 19.99, 'Ropa', 50, true, 1, NOW()),
  ('Pantalón Vaquero Slim', 'Vaquero slim fit de denim elástico. Disponible en azul y negro.', 49.99, 'Ropa', 30, true, 1, NOW()),
  ('Zapatillas Running Pro', 'Zapatillas de running con amortiguación avanzada y suela antideslizante.', 89.99, 'Calzado', 20, true, 1, NOW()),
  ('Mochila Urbana 20L', 'Mochila impermeable con compartimento para portátil hasta 15 pulgadas.', 39.99, 'Accesorios', 15, true, 1, NOW()),
  ('Gorra Snapback', 'Gorra ajustable de algodón con visera plana. Varios colores disponibles.', 14.99, 'Accesorios', 100, true, 1, NOW())
ON CONFLICT DO NOTHING;

INSERT INTO storesetting (key, value, description, updated_at)
VALUES
  ('store_name', 'TiendaDemo', 'Nombre de la tienda', NOW()),
  ('store_address', 'Calle Ejemplo 123, Madrid, España', 'Dirección física de la tienda', NOW()),
  ('opening_hours', 'Lunes a Viernes: 9:00 - 20:00 | Sábado: 10:00 - 14:00 | Domingo: Cerrado', 'Horario de apertura', NOW()),
  ('payment_methods', 'Tarjeta de crédito/débito, PayPal, Transferencia bancaria, Bizum', 'Métodos de pago aceptados', NOW()),
  ('return_policy', 'Devoluciones gratuitas en los primeros 30 días desde la compra. El producto debe estar en su estado original.', 'Política de devoluciones', NOW()),
  ('shipping_info', 'Envío gratuito en pedidos superiores a 50€. Entrega en 24-48 horas laborables.', 'Información de envío', NOW()),
  ('contact_email', 'contacto@tiendademo.com', 'Email de contacto', NOW()),
  ('contact_phone', '+34 91 123 45 67', 'Teléfono de contacto', NOW())
ON CONFLICT (key) DO NOTHING;
