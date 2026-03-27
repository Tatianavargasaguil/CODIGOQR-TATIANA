#!/usr/bin/env python3
"""
Script para migrar direcciones a registros existentes usando reverse geocoding
Obtiene las coordenadas de cada registro y genera la dirección completa
"""

import requests
import time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Configuración de conexión a PostgreSQL
DATABASE_URL = "postgresql://qr_user:qr_pass@localhost:5433/qr_db_nueva"

# Crear conexión
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def reverse_geocoding(latitude, longitude):
    """
    Realiza reverse geocoding usando Nominatim (OpenStreetMap)
    Retorna la dirección completa o None si falla
    """
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={latitude}&lon={longitude}"
        headers = {
            'Accept-Language': 'es',
            'User-Agent': 'QRTracker/1.0'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Intentar construir dirección desde componentes
            if 'address' in data:
                addr = data['address']
                partes = []
                
                if addr.get('road'):
                    partes.append(addr['road'])
                if addr.get('house_number'):
                    partes.append(addr['house_number'])
                if addr.get('neighbourhood'):
                    partes.append(addr['neighbourhood'])
                if addr.get('suburb'):
                    partes.append(addr['suburb'])
                if addr.get('city'):
                    partes.append(addr['city'])
                if addr.get('county'):
                    partes.append(addr['county'])
                if addr.get('state'):
                    partes.append(addr['state'])
                
                if partes:
                    return ", ".join(partes)
            
            # Fallback a display_name
            return data.get('display_name', f"{latitude:.6f}, {longitude:.6f}")
        else:
            print(f"  ⚠️  Error HTTP {response.status_code}")
            return None
            
    except Exception as e:
        print(f"  ❌ Error en reverse geocoding: {str(e)}")
        return None

def migrate_direcciones():
    """
    Migra direcciones para todos los registros sin dirección
    """
    session = Session()
    
    try:
        print("\n" + "="*80)
        print("🔄 MIGRANDO DIRECCIONES A REGISTROS EXISTENTES")
        print("="*80 + "\n")
        
        # Obtener todos los registros sin dirección
        query = text("""
            SELECT id, latitude, longitude, origen, destino, created_at 
            FROM locations 
            WHERE direccion_completa IS NULL OR direccion_completa = ''
            ORDER BY created_at DESC
        """)
        
        resultados = session.execute(query).fetchall()
        
        if not resultados:
            print("✅ No hay registros para migrar. Todas las direcciones están completas.\n")
            return
        
        print(f"📍 Se encontraron {len(resultados)} registros sin dirección\n")
        
        migradas = 0
        errores = 0
        
        for idx, row in enumerate(resultados, 1):
            location_id, latitude, longitude, origen, destino, created_at = row
            
            print(f"[{idx}/{len(resultados)}] ID: {location_id}")
            print(f"    Coordenadas: {latitude:.6f}, {longitude:.6f}")
            print(f"    Origen: {origen} → Destino: {destino}")
            print(f"    Fecha: {created_at}")
            print(f"    Obteniendo dirección...", end=" ", flush=True)
            
            # Hacer reverse geocoding
            direccion = reverse_geocoding(latitude, longitude)
            
            if direccion:
                print(f"✅")
                print(f"    Dirección: {direccion}\n")
                
                # Actualizar base de datos
                update_query = text("""
                    UPDATE locations 
                    SET direccion_completa = :direccion 
                    WHERE id = :id
                """)
                
                session.execute(update_query, {"direccion": direccion, "id": location_id})
                session.commit()
                
                migradas += 1
            else:
                print(f"❌")
                print(f"    No se pudo obtener la dirección\n")
                errores += 1
            
            # Rate limiting para Nominatim (máximo 1 request por segundo)
            time.sleep(1.1)
        
        print("="*80)
        print(f"✅ MIGRACIÓN COMPLETADA")
        print(f"   • Direcciones migradas: {migradas}")
        print(f"   • Errores: {errores}")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error durante la migración: {str(e)}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    migrate_direcciones()
