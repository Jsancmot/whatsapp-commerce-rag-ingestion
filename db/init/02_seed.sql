-- 02_seed.sql
-- Real data for Vandalo Var Xàtiva.
-- Runs after 01_schema.sql (PostgreSQL executes init scripts alphabetically).

INSERT INTO product (name, description, price, category, image_url, stock, is_available, version, created_at, updated_at)
VALUES
  -- Tostadas (Desayunos)
  ('Tostada Aceite y Sal', 'Tostada de aceite de oliva y sal.', 2.30, 'Tostadas', NULL, 100, true, 1, NOW(), NOW()),
  ('Tostada Tomate, Aceite y Sal', 'Tostada de tomate, aceite de oliva y sal.', 2.80, 'Tostadas', NULL, 100, true, 1, NOW(), NOW()),
  ('Tostada Jamón y Tomate', 'Tostada de jamón, tomate y aceite de oliva.', 3.40, 'Tostadas', NULL, 100, true, 1, NOW(), NOW()),
  ('Tostada Salmón y Aguacate', 'Tostada de salmón, aguacate y queso feta.', 5.20, 'Tostadas', NULL, 100, true, 1, NOW(), NOW()),
  ('Tostada Huevos Revueltos', 'Tostada de huevos revueltos, tomate y rúcula.', 4.80, 'Tostadas', NULL, 100, true, 1, NOW(), NOW()),

  -- Vandalos (Bocadillos)
  ('Parrillero', 'Panceta o ternera, patatas fritas, pimiento verde, huevo frito y mayonesa.', 9.00, 'Bocadillos', NULL, 100, true, 1, NOW(), NOW()),
  ('Vrascada', 'Ternera, cebolla caramelizada y jamón serrano a la plancha.', 9.00, 'Bocadillos', NULL, 100, true, 1, NOW(), NOW()),
  ('Chivito', 'Lomo o pollo a la plancha, bacon, huevo, lechuga, tomate, queso y mayonesa.', 8.50, 'Bocadillos', NULL, 100, true, 1, NOW(), NOW()),
  ('Canalla', 'Secreto a la brasa, queso manchego, cebolla caramelizada, jamón a la plancha y mayonesa.', 9.00, 'Bocadillos', NULL, 100, true, 1, NOW(), NOW()),
  ('Socarrat', 'Ternera fina, ajos tiernos, queso manchego y tomate rallado.', 9.00, 'Bocadillos', NULL, 100, true, 1, NOW(), NOW()),

  -- Para Picar (Tapas)
  ('Patatas Bravas', 'Con nuestra salsa brava casera, allioli y aceite de pimentón de la Vera.', 7.80, 'Tapas', NULL, 100, true, 1, NOW(), NOW()),
  ('Torrezno', 'Crujiente por fuera y jugoso por dentro, con mayonesa cítrica.', 8.50, 'Tapas', NULL, 100, true, 1, NOW(), NOW()),
  ('Ensaladilla de Langostino', 'Ensaladilla de langostino a nuestro estilo, textura cremosa.', 8.20, 'Tapas', NULL, 100, true, 1, NOW(), NOW()),
  ('Croquetas (Unidad)', 'Opciones: chuleta, gambón, setas y trufa, o puchero (mín. 4 uds).', 2.00, 'Tapas', NULL, 400, true, 1, NOW(), NOW()),
  ('Pulpo a la Brasa', 'Patita de pulpo a la brasa sobre parmentier cremoso.', 9.00, 'Tapas', NULL, 100, true, 1, NOW(), NOW()),

  -- Burgers
  ('Emmyleven Burger', '180gr vaca rubia nacional, queso cheddar, relish de pepinillos, salsa emmy y cebolla caramelizada.', 13.90, 'Burgers', NULL, 100, true, 1, NOW(), NOW()),
  ('Sublime Burger', '180gr vaca rubia nacional, mantequilla trufada, queso semicurado, papada ibérica Joselito.', 15.90, 'Burgers', NULL, 100, true, 1, NOW(), NOW()),

  -- Carnes y Pescados
  ('Chuletón Vaca Madurada', 'Chuletón de vaca madurada 45 días a la brasa con guarnición (aprox 450gr).', 35.00, 'Principales', NULL, 100, true, 1, NOW(), NOW()),
  ('Bacalao al Horno', 'Bacalao con allioli de lima, miel y quicos troceados.', 18.00, 'Principales', NULL, 100, true, 1, NOW(), NOW()),

  -- Bebidas
  ('Cerveza Turia (Tercio)', 'Tercio de cerveza Turia.', 2.90, 'Bebidas', NULL, 200, true, 1, NOW(), NOW()),
  ('Coca-Cola', 'Refresco de cola 33cl.', 2.70, 'Bebidas', NULL, 200, true, 1, NOW(), NOW()),
  ('Vino Obejita Verde (Verdejo)', 'Vino blanco D.O. Utiel-Requena.', 13.00, 'Bebidas', NULL, 50, true, 1, NOW(), NOW())
ON CONFLICT DO NOTHING;

INSERT INTO storesetting (key, value, description, updated_at)
VALUES
  ('store_name', 'Vandalo Var Xàtiva', 'Nombre de la tienda', NOW()),
  ('store_address', 'Calle Professor Sanchis Guarner, 2, bajo, 46800 Xàtiva, Valencia, España', 'Dirección física de la tienda', NOW()),
  ('opening_hours', 'Lunes a Jueves: 09:00 - 00:00 | Viernes a Domingo: 09:00 - 01:30 (Basado en horario habitual de restauración)', 'Horario de apertura', NOW()),
  ('payment_methods', 'Efectivo, Tarjeta de crédito/débito, Bizum (Confirmar en local)', 'Métodos de pago aceptados', NOW()),
  ('return_policy', 'Al tratarse de productos de alimentación, no se admiten devoluciones una vez consumidos o fuera del local sin causa justificada.', 'Política de devoluciones', NOW()),
  ('shipping_info', 'Pedidos para recoger en local o a través de plataformas de delivery locales.', 'Información de envío/recogida', NOW()),
  ('contact_email', 'vandalovar@gmail.com', 'Email de contacto', NOW()),
  ('contact_phone', '+34 622 93 24 01', 'Teléfono de contacto', NOW())
ON CONFLICT (key) DO NOTHING;
