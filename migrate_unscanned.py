"""
Script para migrar la base de datos: Agregar tabla unscanned_vehicles
Propósito: Registrar vehículos que NO fueron escaneados
"""
import sqlite3
import sys

def migrate():
    """Ejecuta la migración"""
    try:
        # Conectar a la base de datos
        conn = sqlite3.connect("./app.db")
        cursor = conn.cursor()
        
        # Crear tabla unscanned_vehicles
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS unscanned_vehicles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id INTEGER NOT NULL,
                responsable_esperado VARCHAR(255),
                verificado_por VARCHAR(255),
                motivo TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles (id)
            )
        """)
        
        # Crear índices
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_unscanned_vehicle_id 
            ON unscanned_vehicles(vehicle_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_unscanned_created_at 
            ON unscanned_vehicles(created_at)
        """)
        
        conn.commit()
        conn.close()
        
        print("✅ Migración completada exitosamente")
        print("✓ Tabla 'unscanned_vehicles' creada")
        print("✓ Índices creados")
        return True
        
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        return False

if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
