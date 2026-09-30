#!/usr/bin/env python3
"""
Script para limpiar registros duplicados de la tabla de ubicaciones.
Elimina registros vacíos (sin datos de formulario) cuando hay múltiples registros del mismo vehículo en el mismo día.

Uso:
    python cleanup_duplicates.py
"""

from app.db import SessionLocal, engine
from app.models import Base, Vehicle, Location
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import func

# Bogotá timezone
bogota_tz = ZoneInfo("America/Bogota")

def cleanup_duplicate_locations():
    """
    Limpia registros duplicados de ubicaciones.
    Mantiene el registro más completo y elimina los vacíos.
    """
    db = SessionLocal()
    
    try:
        # Obtener todos los vehículos
        vehicles = db.query(Vehicle).all()
        total_deleted = 0
        
        print("=" * 60)
        print("[LIMPIEZA] Iniciando limpieza de registros duplicados")
        print("=" * 60)
        
        for vehicle in vehicles:
            # Agrupar por día todos los escaneos de este vehículo
            locations = db.query(Location).filter(
                Location.vehicle_id == vehicle.id
            ).order_by(Location.created_at.asc()).all()
            
            if not locations or len(locations) < 2:
                continue
            
            # Agrupar por día
            days = {}
            for loc in locations:
                day = loc.created_at.date()
                if day not in days:
                    days[day] = []
                days[day].append(loc)
            
            # Para cada día con múltiples registros
            for day, locs_in_day in days.items():
                if len(locs_in_day) < 2:
                    continue
                
                # Clasificar: cuáles tienen datos y cuáles no
                with_data = []
                without_data = []
                
                for loc in locs_in_day:
                    # Contar campos con datos
                    data_count = (
                        (1 if loc.responsable_origen else 0) +
                        (1 if loc.responsable_destino else 0) +
                        (1 if loc.origen else 0) +
                        (1 if loc.destino else 0) +
                        (1 if loc.nivel_gasolina else 0) +
                        (1 if loc.kilometraje else 0) +
                        (1 if loc.direccion_completa else 0)
                    )
                    
                    if data_count >= 2:  # Consideramos "con datos" si tiene 2+ campos
                        with_data.append((loc, data_count))
                    else:
                        without_data.append(loc)
                
                # Si hay registros sin datos, eliminarlos
                if without_data and (with_data or len(locs_in_day) > 2):
                    for loc in without_data:
                        print(f"[DELETE] {vehicle.name} ({vehicle.code}) - {loc.created_at.date()}")
                        print(f"         ID: {loc.id} | Responsable: {loc.responsable_origen} | Hora: {loc.created_at.time()}")
                        db.delete(loc)
                        total_deleted += 1
                        db.commit()
                
                # Si todos tienen datos pero hay múltiples, mantener el más completo
                elif len(with_data) > 1:
                    # Ordenar por cantidad de datos (descendente) y mantener el primero
                    with_data.sort(key=lambda x: x[1], reverse=True)
                    
                    # Eliminar los demás
                    for loc, data_count in with_data[1:]:
                        print(f"[DELETE] {vehicle.name} ({vehicle.code}) - {loc.created_at.date()}")
                        print(f"         ID: {loc.id} | Campos: {data_count} | Hora: {loc.created_at.time()}")
                        db.delete(loc)
                        total_deleted += 1
                        db.commit()
        
        print("\n" + "=" * 60)
        print("[SUCCESS] Limpieza completada")
        print(f"[STATS] Total registros eliminados: {total_deleted}")
        print("=" * 60)
        
        return total_deleted
        
    except Exception as e:
        print(f"[ERROR] Error durante la limpieza: {e}")
        db.rollback()
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    # Crear tablas si no existen
    Base.metadata.create_all(bind=engine)
    
    # Ejecutar limpieza
    cleanup_duplicate_locations()
