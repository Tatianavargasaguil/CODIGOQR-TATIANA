-- Migración: Agregar tabla unscanned_vehicles
-- Propósito: Registrar vehículos que NO fueron escaneados por los movilizadores

CREATE TABLE IF NOT EXISTS unscanned_vehicles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id INTEGER NOT NULL,
    responsable_esperado VARCHAR(255),
    verificado_por VARCHAR(255),
    motivo TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles (id)
);

-- Índices para búsquedas rápidas
CREATE INDEX IF NOT EXISTS idx_unscanned_vehicle_id ON unscanned_vehicles(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_unscanned_created_at ON unscanned_vehicles(created_at);
