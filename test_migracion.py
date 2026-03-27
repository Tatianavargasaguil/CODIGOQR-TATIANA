#!/usr/bin/env python3
"""Script simple para probar la migración de un registro"""

import requests
import time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://qr_user:qr_pass@localhost:5433/qr_db_nueva"

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def reverse_geocoding(latitude, longitude):
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={latitude}&lon={longitude}"
        headers = {
            'Accept-Language': 'es',
            'User-Agent': 'QRTracker/1.0'
        }
        print(f"  Llamando a Nominatim...")
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'address' in data:
                addr = data['address']
                partes = []
                if addr.get('road'): partes.append(addr['road'])
                if addr.get('house_number'): partes.append(addr['house_number'])
                if addr.get('neighbourhood'): partes.append(addr['neighbourhood'])
                if addr.get('suburb'): partes.append(addr['suburb'])
                if addr.get('city'): partes.append(addr['city'])
                if partes:
                    return ", ".join(partes)
            return data.get('display_name', f"{latitude:.6f}, {longitude:.6f}")
        else:
            print(f"  Error HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"  Error: {str(e)}")
        return None

# Test
session = Session()
print("Conectando a BD...")
query = text("SELECT id, latitude, longitude FROM locations WHERE id = 147 LIMIT 1")
result = session.execute(query).fetchone()

if result:
    id, lat, lon = result
    print(f"Registro encontrado: ID={id}, Lat={lat}, Lon={lon}")
    
    print("Haciendo reverse geocoding...")
    direccion = reverse_geocoding(lat, lon)
    
    if direccion:
        print(f"Dirección obtenida: {direccion}")
        print("Actualizando BD...")
        update = text("UPDATE locations SET direccion_completa = :dir WHERE id = :id")
        session.execute(update, {"dir": direccion, "id": id})
        session.commit()
        print("✅ Actualizado!")
    else:
        print("❌ No se pudo obtener dirección")
else:
    print("No se encontraron registros")

session.close()
