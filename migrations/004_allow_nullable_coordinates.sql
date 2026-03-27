-- Migración para permitir NULL en latitude y longitude
-- Permite guardar ubicaciones sin coordenadas GPS

ALTER TABLE locations 
ALTER COLUMN latitude DROP NOT NULL;

ALTER TABLE locations 
ALTER COLUMN longitude DROP NOT NULL;
