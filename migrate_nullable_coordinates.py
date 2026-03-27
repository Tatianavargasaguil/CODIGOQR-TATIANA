#!/usr/bin/env python3
"""
Script de migración para permitir NULL en latitude y longitude
Ejecuta: python migrate_nullable_coordinates.py
"""

import os
from sqlalchemy import text
from app.db import engine

def migrate():
    """Ejecuta la migración para hacer latitude y longitude nullable"""
    
    print("🔄 Iniciando migración: nullable coordinates...")
    
    try:
        with engine.connect() as connection:
            # Ejecutar la migración
            connection.execute(text("""
                ALTER TABLE locations 
                ALTER COLUMN latitude DROP NOT NULL
            """))
            
            connection.execute(text("""
                ALTER TABLE locations 
                ALTER COLUMN longitude DROP NOT NULL
            """))
            
            connection.commit()
            
            print("✅ Migración completada exitosamente!")
            print("   - latitude ahora puede ser NULL")
            print("   - longitude ahora puede ser NULL")
            
    except Exception as e:
        print(f"❌ Error en la migración: {e}")
        print("\n💡 Si recibes error de 'already null' es porque ya estaba hecho.")
        return False
    
    return True

if __name__ == "__main__":
    migrate()
