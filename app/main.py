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
from .models import Vehicle, Location
from .schemas import LocationCreate, VehicleCreate
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


# 🔹 PÁGINA PARA GENERAR CÓDIGOS QR
@app.get("/generar-qr", response_class=HTMLResponse)
def generar_qr_page(request: Request, user: str = Depends(login_required)):
    return templates.TemplateResponse("generar_qr.html", {"request": request})


# 🔹 PÁGINA PARA VER HISTORIAL DE UBICACIONES
@app.get("/historial", response_class=HTMLResponse)
def historial_page(request: Request, user: str = Depends(login_required)):
    return templates.TemplateResponse("historial.html", {"request": request})


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