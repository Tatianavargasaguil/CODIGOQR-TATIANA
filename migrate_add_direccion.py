#!/usr/bin/env python3
"""
Script de migración para agregar la columna direccion_completa a locations
Ejecutar: python migrate_add_direccion.py
"""

import os
import sys
from sqlalchemy import text, inspect
from sqlalchemy.orm import Session

# Agregar el directorio app al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.db import engine
from app.models import Location

def migrate_add_direccion_completa():
    """Agrega la columna direccion_completa a la tabla locations si no existe"""
    
    with engine.begin() as connection:
        # Inspeccionar las columnas existentes
        inspector = inspect(engine)
        columns = inspector.get_columns('locations')
        column_names = [col['name'] for col in columns]
        
        print(f"✓ Columnas actuales en 'locations': {column_names}")
        
        # Verificar si la columna ya existe
        if 'direccion_completa' in column_names:
            print("✓ La columna 'direccion_completa' ya existe. Migración cancelada.")
            return True
        
        # Agregar la columna
        print("⏳ Agregando columna 'direccion_completa'...")
        connection.execute(text("""
            ALTER TABLE locations 
            ADD COLUMN direccion_completa VARCHAR NULL
        """))
        connection.commit()
        
        print("✓ Columna 'direccion_completa' agregada exitosamente")
        print("✓ Todos los registros existentes se han mantenido")
        return True

if __name__ == "__main__":
    try:
        print("=" * 60)
        print("MIGRACIÓN: Agregar campo direccion_completa")
        print("=" * 60)
        
        migrate_add_direccion_completa()
        
        print("\n" + "=" * 60)
        print("✓ MIGRACIÓN COMPLETADA EXITOSAMENTE")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ ERROR en la migración: {e}", file=sys.stderr)
        sys.exit(1)
