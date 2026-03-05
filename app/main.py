import os
import secrets
from fastapi import FastAPI, Depends, Request, HTTPException, status, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
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
            "vehicle_id": vehicle.id,
            "origen": vehicle.origen,
            "destino": vehicle.destino,
            "responsable_origen": vehicle.responsable_origen,
            "responsable_destino": vehicle.responsable_destino,
            "nivel_gasolina": vehicle.nivel_gasolina,
            "kilometraje": vehicle.kilometraje,
            "observaciones": vehicle.observaciones
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
        origen=data.origen,
        destino=data.destino,
        responsable_origen=data.responsable_origen,
        responsable_destino=data.responsable_destino,
        nivel_gasolina=data.nivel_gasolina,
        kilometraje=data.kilometraje,
        observaciones=data.observaciones,
    )
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    
    return {
        "success": True,
        "vehicle_id": vehicle.id,
        "vehicle_code": vehicle.code,
        "vehicle_name": vehicle.name,
        "origen": vehicle.origen,
        "destino": vehicle.destino,
        "responsable_origen": vehicle.responsable_origen,
        "responsable_destino": vehicle.responsable_destino,
        "nivel_gasolina": vehicle.nivel_gasolina,
        "kilometraje": vehicle.kilometraje,
        "observaciones": vehicle.observaciones,
    }


# 🔹 ACTUALIZAR CAMPOS ADICIONALES DE VEHÍCULO EXISTENTE (protegido)
@app.post("/api/update-vehicle/{vehicle_code}")
def update_vehicle(vehicle_code: str, data: VehicleCreate, db: Session = Depends(get_db), user: str = Depends(login_required)):
    """Actualiza los campos adicionales de un vehículo existente (origen, destino, responsables, etc)
    Sin cambiar el código QR ni el nombre del vehículo"""
    vehicle = db.query(Vehicle).filter(Vehicle.code == vehicle_code).first()
    if not vehicle:
        return {"error": "Vehículo no encontrado"}
    
    # Actualizar solo campos permitidos (no code ni name)
    vehicle.origen = data.origen
    vehicle.destino = data.destino
    vehicle.responsable_origen = data.responsable_origen
    vehicle.responsable_destino = data.responsable_destino
    vehicle.nivel_gasolina = data.nivel_gasolina
    vehicle.kilometraje = data.kilometraje
    vehicle.observaciones = data.observaciones
    
    db.commit()
    db.refresh(vehicle)
    
    return {
        "success": True,
        "vehicle_code": vehicle.code,
        "vehicle_name": vehicle.name,
        "origen": vehicle.origen,
        "destino": vehicle.destino,
        "responsable_origen": vehicle.responsable_origen,
        "responsable_destino": vehicle.responsable_destino,
        "nivel_gasolina": vehicle.nivel_gasolina,
        "kilometraje": vehicle.kilometraje,
        "observaciones": vehicle.observaciones,
    }


# 🔹 GUARDAR UBICACIÓN CON CONFIRMACIÓN (protegido)
@app.post("/api/save-location/{vehicle_code}")
def save_location(vehicle_code: str, data: LocationCreate, db: Session = Depends(get_db), user: str = Depends(login_required)):
    """Guarda la ubicación GPS del vehículo después de confirmación"""
    vehicle = db.query(Vehicle).filter(Vehicle.code == vehicle_code).first()
    
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    
    location = Location(
        vehicle_id=vehicle.id,
        latitude=data.latitude,
        longitude=data.longitude
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


# 🔹 OBTENER HISTORIAL COMPLETO DE UBICACIONES POR CÓDIGO
@app.get("/api/historial/{vehicle_code}")
def get_historial(vehicle_code: str, db: Session = Depends(get_db)):
    """Obtiene el historial completo de ubicaciones de un vehículo usando su código"""
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
            "vehicle_code": vehicle_code,
            "vehicle_name": vehicle.name,
            "origen": vehicle.origen,
            "destino": vehicle.destino,
            "responsable_origen": vehicle.responsable_origen,
            "responsable_destino": vehicle.responsable_destino,
            "nivel_gasolina": vehicle.nivel_gasolina,
            "kilometraje": vehicle.kilometraje,
            "observaciones": vehicle.observaciones,
            "total_registros": 0,
            "locations": [],
            "message": "No hay registros de ubicación"
        }
    
    return {
        "vehicle_code": vehicle_code,
        "vehicle_name": vehicle.name,
        "origen": vehicle.origen,
        "destino": vehicle.destino,
        "responsable_origen": vehicle.responsable_origen,
        "responsable_destino": vehicle.responsable_destino,
        "nivel_gasolina": vehicle.nivel_gasolina,
        "kilometraje": vehicle.kilometraje,
        "observaciones": vehicle.observaciones,
        "total_registros": len(locations),
        "locations": [
            {
                "latitude": loc.latitude,
                "longitude": loc.longitude,
                "timestamp": to_bogota(loc.created_at),
                "fecha_formateada": to_bogota(loc.created_at).strftime("%d/%m/%Y %H:%M:%S")
            }
            for loc in locations
        ]
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
            "origen": vehicle.origen,
            "destino": vehicle.destino,
            "responsable_origen": vehicle.responsable_origen,
            "responsable_destino": vehicle.responsable_destino,
            "nivel_gasolina": vehicle.nivel_gasolina,
            "kilometraje": vehicle.kilometraje,
            "observaciones": vehicle.observaciones,
            "total_registros": 0,
            "locations": [],
            "message": "No hay registros de ubicación"
        }
    
    return {
        "vehicle_code": vehicle.code,
        "vehicle_name": vehicle.name,
        "origen": vehicle.origen,
        "destino": vehicle.destino,
        "responsable_origen": vehicle.responsable_origen,
        "responsable_destino": vehicle.responsable_destino,
        "nivel_gasolina": vehicle.nivel_gasolina,
        "kilometraje": vehicle.kilometraje,
        "observaciones": vehicle.observaciones,
        "total_registros": len(locations),
        "locations": [
            {
                "latitude": loc.latitude,
                "longitude": loc.longitude,
                "timestamp": to_bogota(loc.created_at),
                "fecha_formateada": to_bogota(loc.created_at).strftime("%d/%m/%Y %H:%M:%S")
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