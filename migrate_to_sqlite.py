"""
Script para migrar a SQLite y crear la tabla unscanned_vehicles
"""
import sqlite3
import sys
import os

def migrate():
    """Ejecuta la migración a SQLite"""
    try:
        # Conectar a la base de datos SQLite (se crea si no existe)
        # Usa la ruta relativa desde app/db.py
        db_path = os.path.join(os.path.dirname(__file__), "app.db")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print(f"📁 Base de datos: {db_path}")
        
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
        print("✓ SQLite está listo para usar")
        return True
        
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        return False

if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
