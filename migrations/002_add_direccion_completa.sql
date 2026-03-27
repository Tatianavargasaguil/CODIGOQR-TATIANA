-- Migración: Agregar columna direccion_completa a locations
-- Fecha: 2026-03-13
-- Descripción: Agrega el campo de dirección completa obtenida por reverse geocoding

-- Agregar la columna sin perder datos existentes
ALTER TABLE locations ADD COLUMN comentarios_direccion VARCHAR NULL;

-- Alternativamente, si quieres usar el nombre exacto direccion_completa:
ALTER TABLE locations ADD COLUMN direccion_completa VARCHAR NULL;

-- Verificar que la columna se agregó correctamente
-- SELECT * FROM locations LIMIT 1;
