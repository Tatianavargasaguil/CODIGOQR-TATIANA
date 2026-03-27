import os
import secrets
import logging
import tempfile
from fastapi import FastAPI, Depends, Request, HTTPException, status, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from .db import engine, Base, get_db
from .models import Vehicle, Location, UnscannedVehicle
from .schemas import LocationCreate, VehicleCreate, UnscannedVehicleCreate
import uuid
from dotenv import load_dotenv
import pandas as pd

# load environment variables from .env if it exists
load_dotenv()

# credentials and configuration (override in .env)
USERNAME = os.getenv("ADMIN_USER", "admin")
PASSWORD = os.getenv("ADMIN_PASS", "secret")
SESSION_SECRET = os.getenv("SESSION_SECRET", "change_this_secret")

# CORS origins can be a comma-separated list in .env
raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:8001")
ALLOWED_ORIGINS = [o.strip() for o in raw_origins.split(",") if o.strip()]

from datetime import timezone, datetime
from zoneinfo import ZoneInfo  # available in Python 3.9+

# Bogotá timezone helper
bogota_tz = ZoneInfo("America/Bogota")

def to_bogota(dt: datetime) -> datetime:
    """Convert a UTC or naive datetime to Bogotá local time."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        # assume stored value is UTC
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(bogota_tz)

Base.metadata.create_all(bind=engine)

app = FastAPI()

# Session middleware for simple login state
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)

# CORS Configuration (use ALLOWED_ORIGINS from env; default to localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")


def login_required(request: Request):
    """Dependency for protecting routes behind a simple session login."""
    user = request.session.get("user")
    if not user:
        # redirect to login page if not authenticated
        raise HTTPException(status_code=status.HTTP_302_FOUND, headers={"Location": "/login"})
    return user


@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login", response_class=HTMLResponse)
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """Validate credentials and establish session."""
    if secrets.compare_digest(username, USERNAME) and secrets.compare_digest(password, PASSWORD):
        request.session["user"] = username
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    # invalid -> re-render with error message
    return templates.TemplateResponse("login.html", {"request": request, "error": "Usuario o contraseña incorrectos"})


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)


# 🔹 PÁGINA PRINCIPAL - Escaneo QR unificado
@app.get("/", response_class=HTMLResponse)
def index(request: Request, user: str = Depends(login_required)):
    return templates.TemplateResponse("scan.html", {"request": request})


# 🔹 PÁGINA DE CONTROL DE PUERTA
@app.get("/puerta", response_class=HTMLResponse)
def puerta_control(request: Request, user: str = Depends(login_required)):
    return templates.TemplateResponse("puerta.html", {"request": request})


# 🔹 PÁGINA PARA GENERAR CÓDIGOS QR
@app.get("/generar-qr", response_class=HTMLResponse)
def generar_qr_page(request: Request, user: str = Depends(login_required)):
    return templates.TemplateResponse("generar_qr.html", {"request": request})


# 🔹 PÁGINA PARA VER HISTORIAL DE UBICACIONES
@app.get("/historial", response_class=HTMLResponse)
def historial_page(request: Request, user: str = Depends(login_required)):
    return templates.TemplateResponse("historial.html", {"request": request})


# 🔹 PÁGINA PARA VER REPORTES POR DÍA
@app.get("/reportes-diarios", response_class=HTMLResponse)
def reportes_diarios_page(request: Request, user: str = Depends(login_required)):
    return templates.TemplateResponse("reportes_diarios.html", {"request": request})


# 🔹 API PARA GENERAR CÓDIGO QR (protegido)
@app.post("/api/generar-qr")
def generar_codigo_qr(user: str = Depends(login_required)):
    """Genera un código QR único para un vehículo"""
    import qrcode
    from io import BytesIO
    import base64
    
    # Generar código único
    codigo_qr = "veh_" + uuid.uuid4().hex[:8]
    
    # Crear imagen QR (requiere pillow para manipular imágenes)
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(codigo_qr)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convertir a base64
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode()
    
    return {
        "success": True,
        "codigo_qr": codigo_qr,
        "qr_image": f"data:image/png;base64,{img_base64}",
        "mensaje": f"Código QR generado. Imprime o captura esta imagen y pégala en tu vehículo."
    }


# 🔹 LISTAR TODOS LOS VEHÍCULOS REGISTRADOS (protegido)
@app.get("/api/list-vehicles")
def list_vehicles(db: Session = Depends(get_db), user: str = Depends(login_required)):
    """Lista todos los vehículos registrados con sus códigos QR"""
    vehicles = db.query(Vehicle).order_by(Vehicle.created_at.desc()).all()
    
    if not vehicles:
        return {
            "total_vehiculos": 0,
            "vehicles": [],
            "mensaje": "No hay vehículos registrados"
        }
    
    return {
        "total_vehiculos": len(vehicles),
        "vehicles": [
            {
                "id": v.id,
                "codigo_qr": v.code,
                "nombre": v.name,
                "fecha_registro": to_bogota(v.created_at).strftime("%d/%m/%Y %H:%M:%S")
            }
            for v in vehicles
        ]
    }


# 🔹 REGENERAR QR PARA UN VEHÍCULO EXISTENTE (Sin perder historial)
@app.post("/api/regenerar-qr/{vehicle_code}")
def regenerar_qr_existente(vehicle_code: str, db: Session = Depends(get_db), user: str = Depends(login_required)):
    """Regenera la imagen QR para un vehículo existente (mantiene el mismo código y historial)"""
    import qrcode
    from io import BytesIO
    import base64
    
    # Limpiar y preparar el código
    vehicle_code = vehicle_code.strip()
    
    # Verificar que el vehículo existe (case-insensitive)
    vehicle = db.query(Vehicle).filter(Vehicle.code.ilike(vehicle_code)).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail=f"Vehículo no encontrado: {vehicle_code}")
    
    # Regenerar la imagen QR con el MISMO código
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(vehicle_code)  # ← MISMO CÓDIGO
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convertir a base64
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode()
    
    return {
        "success": True,
        "codigo_qr": vehicle_code,
        "nombre_vehiculo": vehicle.name,
        "qr_image": f"data:image/png;base64,{img_base64}",
        "mensaje": f"Código QR regenerado para {vehicle.name}. Imprime y reemplaza el papel dañado. ¡El historial se mantiene intacto!"
    }


# 🔹 BUSCAR O CREAR VEHÍCULO POR CÓDIGO QR (protegido)
@app.post("/api/vehicle-qr/{vehicle_code}")
def get_or_create_vehicle(vehicle_code: str, db: Session = Depends(get_db), user: str = Depends(login_required)):
    """Busca un vehículo por código QR. Si existe, retorna sus datos."""
    try:
        vehicle = db.query(Vehicle).filter(Vehicle.code == vehicle_code).first()
    except Exception as e:
        # capture any database/other errors and return JSON instead of 500 HTML
        return JSONResponse(status_code=500, content={"error": str(e)})
    
    if vehicle:
        return {
            "exists": True,
            "vehicle_code": vehicle.code,
            "vehicle_name": vehicle.name,
            "vehicle_id": vehicle.id
        }
    else:
        return {
            "exists": False,
            "vehicle_code": vehicle_code,
            "message": "Nuevo vehículo - Por favor registra el nombre"
        }


# 🔹 REGISTRAR NUEVO VEHÍCULO (protegido)
@app.post("/api/register-vehicle")
def register_vehicle(data: VehicleCreate, db: Session = Depends(get_db), user: str = Depends(login_required)):
    """Registra un nuevo vehículo con el código QR y nombre"""
    # Verificar si ya existe un vehículo con ese código
    existing = db.query(Vehicle).filter(Vehicle.code == data.code).first()
    if existing:
        return {"error": "Este código QR ya está registrado"}
    
    vehicle = Vehicle(
        code=data.code,
        name=data.name,
    )
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    
    return {
        "success": True,
        "vehicle_id": vehicle.id,
        "vehicle_code": vehicle.code,
        "vehicle_name": vehicle.name,
    }


# 🔹 ACTUALIZAR CAMPOS ADICIONALES DE VEHÍCULO EXISTENTE (protegido)
@app.post("/api/update-vehicle/{vehicle_code}")
def update_vehicle(vehicle_code: str, data: VehicleCreate, db: Session = Depends(get_db), user: str = Depends(login_required)):
    """Los datos de formulario ahora se guardan con cada ubicación, no con el vehículo"""
    vehicle = db.query(Vehicle).filter(Vehicle.code == vehicle_code).first()
    if not vehicle:
        return {"error": "Vehículo no encontrado"}
    
    # Solo retornar info del vehículo
    return {
        "success": True,
        "vehicle_code": vehicle.code,
        "vehicle_name": vehicle.name,
    }


# 🔹 GUARDAR UBICACIÓN CON CONFIRMACIÓN (protegido)
@app.post("/api/save-location/{vehicle_code}")
def save_location(vehicle_code: str, data: LocationCreate, db: Session = Depends(get_db), user: str = Depends(login_required)):
    """Guarda la ubicación GPS del vehículo con todos los datos del formulario"""
    vehicle = db.query(Vehicle).filter(Vehicle.code == vehicle_code).first()
    
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    
    # Log para debug
    import sys
    print(f"[DEBUG] save_location recibido: lat={data.latitude}, lon={data.longitude}, origen={data.origen}", file=sys.stderr)
    
    location = Location(
        vehicle_id=vehicle.id,
        latitude=data.latitude,
        longitude=data.longitude,
        origen=data.origen,
        destino=data.destino,
        responsable_origen=data.responsable_origen,
        responsable_destino=data.responsable_destino,
        nivel_gasolina=data.nivel_gasolina,
        kilometraje=data.kilometraje,
        observaciones=data.observaciones,
        direccion_completa=data.direccion_completa,
    )
    
    db.add(location)
    db.commit()
    db.refresh(location)
    
    return {
        "success": True,
        "message": "Ubicación guardada correctamente",
        "location_id": location.id,
        "latitude": location.latitude,
        "longitude": location.longitude,
        "timestamp": location.created_at
    }


# 🔹 OBTENER ÚLTIMO REGISTRO DE UBICACIÓN (protegido)
@app.get("/api/last-location/{vehicle_code}")
def get_last_location(vehicle_code: str, db: Session = Depends(get_db), user: str = Depends(login_required)):
    """Obtiene la última ubicación registrada de un vehículo"""
    vehicle = db.query(Vehicle).filter(Vehicle.code == vehicle_code).first()
    
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    
    last_location = (
        db.query(Location)
        .filter(Location.vehicle_id == vehicle.id)
        .order_by(Location.created_at.desc())
        .first()
    )
    
    if not last_location:
        return {"message": "No hay registro de ubicación"}
    
    return {
        "vehicle_name": vehicle.name,
        "latitude": last_location.latitude,
        "longitude": last_location.longitude,
        "timestamp": to_bogota(last_location.created_at)
    }


# 🔹 OBTENER HISTORIAL COMPLETO DE UBICACIONES POR NOMBRE
@app.get("/api/historial/nombre/{vehicle_name}")
def get_historial_por_nombre(vehicle_name: str, db: Session = Depends(get_db)):
    """Busca un vehículo por nombre (case-insensitive) y retorna su historial"""
    vehicle = (
        db.query(Vehicle)
        .filter(Vehicle.name.ilike(f"%{vehicle_name}%"))
        .first()
    )
    
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    
    locations = (
        db.query(Location)
        .filter(Location.vehicle_id == vehicle.id)
        .order_by(Location.created_at.desc())
        .all()
    )
    
    if not locations:
        return {
            "vehicle_code": vehicle.code,
            "vehicle_name": vehicle.name,
            "total_registros": 0,
            "locations": [],
            "message": "No hay registros de ubicación"
        }
    
    return {
        "vehicle_code": vehicle.code,
        "vehicle_name": vehicle.name,
        "total_registros": len(locations),
        "locations": [
            {
                "latitude": loc.latitude,
                "longitude": loc.longitude,
                "timestamp": to_bogota(loc.created_at),
                "fecha_formateada": to_bogota(loc.created_at).strftime("%d/%m/%Y %H:%M:%S"),
                "origen": loc.origen,
                "destino": loc.destino,
                "responsable_origen": loc.responsable_origen,
                "responsable_destino": loc.responsable_destino,
                "nivel_gasolina": loc.nivel_gasolina,
                "kilometraje": loc.kilometraje,
                "observaciones": loc.observaciones,
                "direccion_completa": loc.direccion_completa,
            }
            for loc in locations
        ]
    }


# 🔹 OBTENER HISTORIAL POR CÓDIGO QR (para dashboard)
@app.get("/api/historial/{vehicle_code}")
def get_historial_por_codigo(vehicle_code: str, db: Session = Depends(get_db)):
    """Obtiene el historial de ubicaciones de un vehículo por su código QR"""
    vehicle = db.query(Vehicle).filter(Vehicle.code == vehicle_code).first()
    
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    
    locations = (
        db.query(Location)
        .filter(Location.vehicle_id == vehicle.id)
        .order_by(Location.created_at.desc())
        .all()
    )
    
    if not locations:
        return {
            "vehicle_code": vehicle.code,
            "vehicle_name": vehicle.name,
            "total_registros": 0,
            "locations": [],
            "message": "No hay registros de ubicación"
        }
    
    return {
        "vehicle_code": vehicle.code,
        "vehicle_name": vehicle.name,
        "total_registros": len(locations),
        "locations": [
            {
                "latitude": loc.latitude,
                "longitude": loc.longitude,
                "timestamp": to_bogota(loc.created_at),
                "fecha_formateada": to_bogota(loc.created_at).strftime("%d/%m/%Y %H:%M:%S"),
                "origen": loc.origen,
                "destino": loc.destino,
                "responsable_origen": loc.responsable_origen,
                "responsable_destino": loc.responsable_destino,
                "nivel_gasolina": loc.nivel_gasolina,
                "kilometraje": loc.kilometraje,
                "observaciones": loc.observaciones,
                "direccion_completa": loc.direccion_completa,
            }
            for loc in locations
        ]
    }


# 🔹 GUARDAR UBICACIÓN MANUALMENTE (desde dashboard)
@app.post("/api/guardar-ubicacion")
def guardar_ubicacion_manual(data: dict, db: Session = Depends(get_db)):
    """Guarda manualmente una ubicación con el botón 'Guardar Ubicación'"""
    vehicle_code = data.get("vehicle_code")
    latitude = data.get("latitude")
    longitude = data.get("longitude")
    
    if not vehicle_code or latitude is None or longitude is None:
        return {"success": False, "error": "Datos incompletos"}
    
    vehicle = db.query(Vehicle).filter(Vehicle.code == vehicle_code).first()
    
    if not vehicle:
        return {"success": False, "error": "Vehículo no encontrado"}
    
    location = Location(
        vehicle_id=vehicle.id,
        latitude=latitude,
        longitude=longitude
    )
    
    db.add(location)
    db.commit()
    db.refresh(location)
    
    return {
        "success": True,
        "message": "Ubicación guardada correctamente",
        "location_id": location.id,
        "latitude": location.latitude,
        "longitude": location.longitude,
        "timestamp": to_bogota(location.created_at)
    }


# 🔹 EXPORTAR A EXCEL CON FILTROS
@app.get("/api/export-excel")
def export_excel(
    vehicle_code: str = None,
    date_from: str = None,
    date_to: str = None,
    db: Session = Depends(get_db),
    user: str = Depends(login_required)
):
    """Exporta registros de ubicación a Excel con filtros de fecha y placa"""
    
    # Construcción de query base
    query = db.query(Location).join(Vehicle)
    
    # Filtro por placa (vehículo) - requerido
    if vehicle_code:
        query = query.filter(Vehicle.code == vehicle_code)
    else:
        raise HTTPException(status_code=400, detail="vehicle_code es requerido")
    
    # Filtro por fechas
    if date_from:
        try:
            date_from_dt = datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            query = query.filter(Location.created_at >= date_from_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de date_from inválido (use YYYY-MM-DD)")
    
    if date_to:
        try:
            date_to_dt = datetime.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
            query = query.filter(Location.created_at <= date_to_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de date_to inválido (use YYYY-MM-DD)")
    
    locations = query.order_by(Location.created_at.desc()).all()
    
    if not locations:
        raise HTTPException(status_code=404, detail="No hay registros que coincidan con los filtros")
    
    # Construir datos para Excel
    data = []
    for idx, loc in enumerate(locations, 1):
        data.append({
            "#": idx,
            "Fecha y Hora": to_bogota(loc.created_at).strftime("%d/%m/%Y %H:%M:%S"),
            "Código": loc.vehicle.code,
            "Vehículo": loc.vehicle.name,
            "Latitud": round(loc.latitude, 6),
            "Longitud": round(loc.longitude, 6),
            "Origen": loc.origen or "",
            "Destino": loc.destino or "",
            "Resp. Origen": loc.responsable_origen or "",
            "Resp. Destino": loc.responsable_destino or "",
            "Nivel Gasolina": loc.nivel_gasolina or "",
            "Kilometraje": loc.kilometraje or "",
            "Observaciones": loc.observaciones or ""
        })
    
    # Crear DataFrame
    df = pd.DataFrame(data)
    
    # Crear archivo Excel
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    excel_path = temp_file.name
    temp_file.close()
    
    # Escribir Excel con formato
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Historial', index=False)
        
        # Acceder a la hoja para ajustar ancho de columnas
        worksheet = writer.sheets['Historial']
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    # Generar nombre del archivo
    if vehicle_code:
        filename = f"Reporte_{vehicle_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    else:
        filename = f"Reporte_Completo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return FileResponse(
        path=excel_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# 🔹 DASHBOARD - Ver historial del vehículo
@app.get("/dashboard/{vehicle_code}", response_class=HTMLResponse)
def dashboard(request: Request, vehicle_code: str, db: Session = Depends(get_db)):
    vehicle = db.query(Vehicle).filter(Vehicle.code == vehicle_code).first()
    
    if not vehicle:
        return HTMLResponse("Vehículo no encontrado", status_code=404)
    
    last_location = (
        db.query(Location)
        .filter(Location.vehicle_id == vehicle.id)
        .order_by(Location.created_at.desc())
        .first()
    )
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "vehicle": vehicle,
        "last_location": last_location
    })


# 🔹 VERIFICAR SI UN VEHÍCULO FUE ESCANEADO HOY
@app.get("/api/check-vehicle-scan/{vehicle_code}")
def check_vehicle_scan(vehicle_code: str, db: Session = Depends(get_db), user: str = Depends(login_required)):
    """
    Verifica si un vehículo fue escaneado HOY
    - Busca por código interno (veh_xxx) O por placa (NHQ928, etc)
    - Si fue escaneado: Retorna info del escaneo
    - Si NO fue escaneado: Permite registrarlo como no escaneado
    """
    from datetime import datetime, timedelta
    
    # Busca por código interno O por placa (name)
    vehicle = db.query(Vehicle).filter(
        (Vehicle.code == vehicle_code) | (Vehicle.name == vehicle_code)
    ).first()
    
    if not vehicle:
        return {
            "found": False,
            "message": "Vehículo no encontrado"
        }
    
    # Buscar si hay escaneo HOY
    today = datetime.now(tz=bogota_tz).date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    today_scan = db.query(Location)\
        .filter(Location.vehicle_id == vehicle.id)\
        .filter(Location.created_at >= today_start)\
        .filter(Location.created_at <= today_end)\
        .order_by(Location.created_at.desc())\
        .first()
    
    if today_scan:
        # SÍ FUE ESCANEADO HOY
        return {
            "found": True,
            "was_scanned": True,
            "vehicle_code": vehicle.code,
            "vehicle_name": vehicle.name,
            "scanned_at": to_bogota(today_scan.created_at).strftime("%H:%M:%S"),
            "location": today_scan.direccion_completa or "Ubicación no disponible",
            "responsable": today_scan.responsable_origen or "No registrado",
            "message": f"✅ {vehicle.name} fue escaneado a las {to_bogota(today_scan.created_at).strftime('%H:%M:%S')}"
        }
    else:
        # NO FUE ESCANEADO HOY
        return {
            "found": True,
            "was_scanned": False,
            "vehicle_code": vehicle.code,
            "vehicle_name": vehicle.name,
            "message": f"❌ {vehicle.name} NO fue escaneado hoy",
            "can_mark_unscanned": True
        }


# 🔹 MARCAR VEHÍCULO COMO NO ESCANEADO
@app.post("/api/mark-unscanned/{vehicle_code}")
def mark_vehicle_unscanned(
    vehicle_code: str,
    data: UnscannedVehicleCreate,
    db: Session = Depends(get_db),
    user: str = Depends(login_required)
):
    """
    Registra que un vehículo NO fue escaneado por su placa (name)
    - responsable_esperado: Quién DEBERÍA haber escaneado (nombre del movilizador)
    - motivo: Razón por la que no fue escaneado (opcional)
    """
    vehicle = db.query(Vehicle).filter(Vehicle.name == vehicle_code).first()
    
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    
    # Crear registro de no escaneado
    unscanned = UnscannedVehicle(
        vehicle_id=vehicle.id,
        responsable_esperado=data.responsable_esperado,
        verificado_por=user,  # Quién registra (persona en puerta)
        motivo=data.motivo
    )
    
    db.add(unscanned)
    db.commit()
    db.refresh(unscanned)
    
    return {
        "success": True,
        "message": f"✗ {vehicle.name} registrado como NO escaneado",
        "vehicle_code": vehicle.code,
        "vehicle_name": vehicle.name,
        "responsable_esperado": data.responsable_esperado,
        "verified_by": user,
        "timestamp": to_bogota(unscanned.created_at).strftime("%d/%m/%Y %H:%M:%S")
    }


# 🔹 OBTENER LISTA DE VEHÍCULOS NO ESCANEADOS HOY
@app.get("/api/unscanned-today")
def get_unscanned_today(db: Session = Depends(get_db), user: str = Depends(login_required)):
    """
    Retorna lista de vehículos que NO fueron escaneados hoy
    Útil para REPORTE de incumplimientos
    """
    from datetime import datetime
    
    today = datetime.now(tz=bogota_tz).date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    # Vehículos no escaneados HOY
    unscanned_today = db.query(UnscannedVehicle)\
        .join(Vehicle)\
        .filter(UnscannedVehicle.created_at >= today_start)\
        .filter(UnscannedVehicle.created_at <= today_end)\
        .order_by(UnscannedVehicle.created_at.desc())\
        .all()
    
    # Total de vehículos registrados
    total_vehicles = db.query(Vehicle).count()
    
    # Vehículos escaneados hoy
    scanned_today = db.query(Vehicle).join(Location)\
        .filter(Location.created_at >= today_start)\
        .filter(Location.created_at <= today_end)\
        .distinct()\
        .count()
    
    return {
        "fecha": str(today),
        "total_vehiculos": total_vehicles,
        "escaneados_hoy": scanned_today,
        "no_escaneados_hoy": len(unscanned_today),
        "tasa_cumplimiento": round((scanned_today / total_vehicles * 100), 2) if total_vehicles > 0 else 0,
        "no_escaneados": [
            {
                "id": u.id,
                "vehicle_code": u.vehicle.code,
                "vehicle_name": u.vehicle.name,
                "responsable_esperado": u.responsable_esperado,
                "verificado_por": u.verificado_por,
                "motivo": u.motivo,
                "registrado_a": to_bogota(u.created_at).strftime("%H:%M:%S")
            }
            for u in unscanned_today
        ]
    }


# 🔹 OBTENER REPORTE COMPLETO DEL DÍA
@app.get("/api/report-daily")
def get_daily_report(db: Session = Depends(get_db), user: str = Depends(login_required)):
    """
    Reporte completo del día: Qué vehículos salieron, cuáles no fueron escaneados, etc.
    """
    from datetime import datetime
    
    today = datetime.now(tz=bogota_tz).date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    # Todos los vehículos
    all_vehicles = db.query(Vehicle).all()
    
    scanned_list = []
    unscanned_list = []
    
    for vehicle in all_vehicles:
        # Buscar escaneo de hoy
        today_scan = db.query(Location)\
            .filter(Location.vehicle_id == vehicle.id)\
            .filter(Location.created_at >= today_start)\
            .filter(Location.created_at <= today_end)\
            .first()
        
        if today_scan:
            scanned_list.append({
                "code": vehicle.code,
                "name": vehicle.name,
                "status": "escaneado",
                "hora": to_bogota(today_scan.created_at).strftime("%H:%M:%S"),
                "responsable": today_scan.responsable_origen or "No registrado",
                "ubicacion": today_scan.direccion_completa or "No disponible"
            })
        else:
            # Buscar si fue registrado como NO escaneado
            unscanned_record = db.query(UnscannedVehicle)\
                .filter(UnscannedVehicle.vehicle_id == vehicle.id)\
                .filter(UnscannedVehicle.created_at >= today_start)\
                .filter(UnscannedVehicle.created_at <= today_end)\
                .first()
            
            if unscanned_record:
                unscanned_list.append({
                    "code": vehicle.code,
                    "name": vehicle.name,
                    "status": "no_escaneado",
                    "responsable_esperado": unscanned_record.responsable_esperado,
                    "verificado_por": unscanned_record.verificado_por,
                    "motivo": unscanned_record.motivo,
                    "registrado_a": to_bogota(unscanned_record.created_at).strftime("%H:%M:%S")
                })
    
    return {
        "fecha": str(today),
        "resumen": {
            "total_vehiculos": len(all_vehicles),
            "escaneados": len(scanned_list),
            "no_escaneados": len(unscanned_list),
            "sin_registro": len(all_vehicles) - len(scanned_list) - len(unscanned_list),
            "tasa_cumplimiento": round((len(scanned_list) / len(all_vehicles) * 100), 2) if len(all_vehicles) > 0 else 0
        },
        "escaneados": scanned_list,
        "no_escaneados": unscanned_list
    }


# 🔹 BUSCAR VEHÍCULOS NO ESCANEADOS CON FILTROS
@app.get("/api/search-unscanned")
def search_unscanned(
    responsable: str = None,
    vehicle_code: str = None,
    vehicle_name: str = None,
    db: Session = Depends(get_db),
    user: str = Depends(login_required)
):
    """
    Busca vehículos NO escaneados hoy con filtros:
    - responsable: Nombre del responsable (búsqueda parcial)
    - vehicle_code: Código del vehículo
    - vehicle_name: Nombre/placa del vehículo (búsqueda parcial)
    """
    from datetime import datetime
    
    today = datetime.now(tz=bogota_tz).date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    query = db.query(UnscannedVehicle).join(Vehicle)\
        .filter(UnscannedVehicle.created_at >= today_start)\
        .filter(UnscannedVehicle.created_at <= today_end)
    
    # Aplicar filtros
    if responsable:
        query = query.filter(UnscannedVehicle.responsable_esperado.ilike(f"%{responsable}%"))
    
    if vehicle_code:
        query = query.filter(Vehicle.code.ilike(f"%{vehicle_code}%"))
    
    if vehicle_name:
        query = query.filter(Vehicle.name.ilike(f"%{vehicle_name}%"))
    
    results = query.order_by(UnscannedVehicle.created_at.desc()).all()
    
    return {
        "total": len(results),
        "filtros_aplicados": {
            "responsable": responsable,
            "vehicle_code": vehicle_code,
            "vehicle_name": vehicle_name
        },
        "resultados": [
            {
                "id": u.id,
                "vehicle_code": u.vehicle.code,
                "vehicle_name": u.vehicle.name,
                "responsable_esperado": u.responsable_esperado,
                "verificado_por": u.verificado_por,
                "motivo": u.motivo,
                "registrado_a": to_bogota(u.created_at).strftime("%H:%M:%S")
            }
            for u in results
        ]
    }


# 🔹 EXPORTAR A EXCEL - VEHÍCULOS NO ESCANEADOS
@app.get("/api/export-unscanned-excel")
def export_unscanned_excel(
    db: Session = Depends(get_db),
    user: str = Depends(login_required)
):
    """
    Exporta a Excel los vehículos NO escaneados de hoy
    """
    from datetime import datetime
    import tempfile
    import os
    
    today = datetime.now(tz=bogota_tz).date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    # Obtener datos
    unscanned = db.query(UnscannedVehicle).join(Vehicle)\
        .filter(UnscannedVehicle.created_at >= today_start)\
        .filter(UnscannedVehicle.created_at <= today_end)\
        .order_by(UnscannedVehicle.created_at.desc())\
        .all()
    
    # Crear DataFrame
    data = []
    for u in unscanned:
        data.append({
            "Placa/Código": u.vehicle.code,
            "Nombre Vehículo": u.vehicle.name,
            "Responsable Esperado": u.responsable_esperado or "No registrado",
            "Verificado Por": u.verificado_por or "No registrado",
            "Motivo": u.motivo or "-",
            "Hora Registro": to_bogota(u.created_at).strftime("%H:%M:%S")
        })
    
    df = pd.DataFrame(data)
    
    # Crear archivo temporal
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    df.to_excel(temp_file.name, index=False, sheet_name="No Escaneados")
    temp_file.close()
    
    # Retornar archivo
    return FileResponse(
        temp_file.name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"no_escaneados_{today}.xlsx"
    )


# 🔹 EXPORTAR A EXCEL - TODOS (ESCANEADOS + NO ESCANEADOS)
@app.get("/api/export-daily-report-excel")
def export_daily_report_excel(
    db: Session = Depends(get_db),
    user: str = Depends(login_required)
):
    """
    Exporta completo el reporte del día a Excel
    """
    from datetime import datetime
    import tempfile
    
    today = datetime.now(tz=bogota_tz).date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    all_vehicles = db.query(Vehicle).all()
    
    data = []
    
    for vehicle in all_vehicles:
        # Buscar escaneo de hoy
        today_scan = db.query(Location)\
            .filter(Location.vehicle_id == vehicle.id)\
            .filter(Location.created_at >= today_start)\
            .filter(Location.created_at <= today_end)\
            .first()
        
        if today_scan:
            data.append({
                "Placa/Código": vehicle.code,
                "Nombre": vehicle.name,
                "Estado": "✅ ESCANEADO",
                "Hora": to_bogota(today_scan.created_at).strftime("%H:%M:%S"),
                "Responsable": today_scan.responsable_origen or "No registrado",
                "Ubicación": today_scan.direccion_completa or "No disponible",
                "Motivo": "-"
            })
        else:
            # Buscar si fue registrado como NO escaneado
            unscanned_record = db.query(UnscannedVehicle)\
                .filter(UnscannedVehicle.vehicle_id == vehicle.id)\
                .filter(UnscannedVehicle.created_at >= today_start)\
                .filter(UnscannedVehicle.created_at <= today_end)\
                .first()
            
            if unscanned_record:
                data.append({
                    "Placa/Código": vehicle.code,
                    "Nombre": vehicle.name,
                    "Estado": "❌ NO ESCANEADO",
                    "Hora": to_bogota(unscanned_record.created_at).strftime("%H:%M:%S"),
                    "Responsable": unscanned_record.responsable_esperado or "No registrado",
                    "Ubicación": "-",
                    "Motivo": unscanned_record.motivo or "-"
                })
            else:
                data.append({
                    "Placa/Código": vehicle.code,
                    "Nombre": vehicle.name,
                    "Estado": "⚠️ SIN REGISTRO",
                    "Hora": "-",
                    "Responsable": "-",
                    "Ubicación": "-",
                    "Motivo": "-"
                })
    
    df = pd.DataFrame(data)
    
    # Crear archivo temporal
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    df.to_excel(temp_file.name, index=False, sheet_name="Reporte Diario")
    temp_file.close()
    
    # Retornar archivo
    return FileResponse(
        temp_file.name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"reporte_diario_{today}.xlsx"
    )


# 🔹 OBTENER ESCANEOS POR FECHA ESPECÍFICA
@app.get("/api/escaneos-por-fecha")
def get_escaneos_por_fecha(
    fecha: str,  # Formato: YYYY-MM-DD
    db: Session = Depends(get_db),
    user: str = Depends(login_required)
):
    """
    Obtiene todos los escaneos de una fecha específica con la información del vehículo
    Retorna: lista de vehículos escaneados ese día con placa y responsables
    """
    from datetime import datetime as dt
    
    try:
        # Parsear la fecha
        fecha_obj = dt.strptime(fecha, "%Y-%m-%d").date()
        
        # Crear rango de tiempo para ese día (00:00:00 a 23:59:59)
        hora_inicio = dt.combine(fecha_obj, dt.min.time()).replace(tzinfo=bogota_tz)
        hora_fin = dt.combine(fecha_obj, dt.max.time()).replace(tzinfo=bogota_tz)
        
        # Obtener todos los vehículos
        todos_vehiculos = db.query(Vehicle).all()
        
        escaneos = []
        no_escaneados = []
        
        for vehiculo in todos_vehiculos:
            # Buscar si el vehículo fue escaneado ese día
            escaneo_dia = (
                db.query(Location)
                .filter(Location.vehicle_id == vehiculo.id)
                .filter(Location.created_at >= hora_inicio)
                .filter(Location.created_at <= hora_fin)
                .first()
            )
            
            if escaneo_dia:
                escaneos.append({
                    "id": escaneo_dia.id,
                    "placa": vehiculo.code,
                    "nombre_vehiculo": vehiculo.name,
                    "hora_escaneo": to_bogota(escaneo_dia.created_at).strftime("%d/%m/%Y %H:%M:%S"),
                    "responsable_origen": escaneo_dia.responsable_origen or "No registrado",
                    "responsable_destino": escaneo_dia.responsable_destino or "No registrado",
                    "origen": escaneo_dia.origen or "-",
                    "destino": escaneo_dia.destino or "-",
                    "nivel_gasolina": escaneo_dia.nivel_gasolina or "-",
                    "kilometraje": escaneo_dia.kilometraje or "-",
                    "observaciones": escaneo_dia.observaciones or "-",
                    "direccion": escaneo_dia.direccion_completa or "No disponible",
                    "latitude": escaneo_dia.latitude,
                    "longitude": escaneo_dia.longitude
                })
            else:
                # Verificar si fue registrado como NO escaneado
                no_escaneo = (
                    db.query(UnscannedVehicle)
                    .filter(UnscannedVehicle.vehicle_id == vehiculo.id)
                    .filter(UnscannedVehicle.created_at >= hora_inicio)
                    .filter(UnscannedVehicle.created_at <= hora_fin)
                    .first()
                )
                
                if no_escaneo:
                    no_escaneados.append({
                        "id": no_escaneo.id,
                        "placa": vehiculo.code,
                        "nombre_vehiculo": vehiculo.name,
                        "responsable_esperado": no_escaneo.responsable_esperado or "-",
                        "verificado_por": no_escaneo.verificado_por or "-",
                        "motivo": no_escaneo.motivo or "No especificado",
                        "hora_registro": to_bogota(no_escaneo.created_at).strftime("%d/%m/%Y %H:%M:%S")
                    })
        
        return {
            "success": True,
            "fecha": fecha,
            "resumen": {
                "total_vehiculos": len(todos_vehiculos),
                "escaneados": len(escaneos),
                "no_escaneados": len(no_escaneados),
                "sin_registro": len(todos_vehiculos) - len(escaneos) - len(no_escaneados),
                "tasa_cumplimiento": round((len(escaneos) / len(todos_vehiculos) * 100), 2) if len(todos_vehiculos) > 0 else 0
            },
            "escaneos": escaneos,
            "no_escaneados": no_escaneados
        }
    
    except ValueError:
        return {
            "success": False,
            "error": "Formato de fecha inválido. Use YYYY-MM-DD (ej: 2026-03-27)"
        }