import os
import secrets
import logging
import tempfile
import time
from fastapi import FastAPI, Depends, Request, HTTPException, status, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.orm import Session
from .db import engine, Base, get_db
from .models import Vehicle, Location, UnscannedVehicle
from .schemas import LocationCreate, VehicleCreate, UnscannedVehicleCreate
from . import cotizador
import uuid
from dotenv import load_dotenv
import pandas as pd

# load environment variables from .env if it exists
load_dotenv()

# credentials and configuration (override in .env)
USERNAME = os.getenv("ADMIN_USER", "admin")
PASSWORD = os.getenv("ADMIN_PASS", "secret")
SESSION_SECRET = os.getenv("SESSION_SECRET", "change_this_secret")
LOGIN_MAX_ATTEMPTS = int(os.getenv("LOGIN_MAX_ATTEMPTS", "5"))
LOGIN_LOCK_SECONDS = int(os.getenv("LOGIN_LOCK_SECONDS", "900"))

def load_admin_users() -> dict[str, str]:
    users = {USERNAME: PASSWORD}
    raw_users = os.getenv("ADMIN_USERS", "")
    for item in raw_users.split(","):
        if ":" not in item:
            continue
        username, password = item.split(":", 1)
        username = username.strip()
        password = password.strip()
        if username and password:
            users[username] = password
    return users


ADMIN_USERS = load_admin_users()
LOGIN_ATTEMPTS: dict[str, dict[str, float | int]] = {}

# CORS origins can be a comma-separated list in .env
raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:8001")
ALLOWED_ORIGINS = [o.strip() for o in raw_origins.split(",") if o.strip() and o.strip() != "*"]

from datetime import timezone, datetime
from zoneinfo import ZoneInfo  # available in Python 3.9+

# BogotÃ¡ timezone helper
bogota_tz = ZoneInfo("America/Bogota")

def to_bogota(dt: datetime) -> datetime:
    """Convert a UTC or naive datetime to BogotÃ¡ local time."""
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
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/manifest.webmanifest")
def pwa_manifest():
    return FileResponse("app/static/manifest.webmanifest", media_type="application/manifest+json")


@app.get("/sw.js")
def pwa_service_worker():
    return FileResponse("app/static/sw.js", media_type="application/javascript")


# âœ… MANEJADOR GLOBAL DE EXCEPCIONES - Devuelve JSON para APIs
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Maneja excepciones HTTP:
    - Si es una ruta de API, devuelve JSON
    - Si es una ruta de HTML, devuelve HTML/redirecciÃ³n
    """
    if request.url.path.startswith("/api/"):
        # Para APIs: devolver JSON siempre
        return JSONResponse(
            status_code=exc.status_code if exc.status_code not in [301, 302, 303, 307, 308] else 401,
            content={
                "error": exc.detail or "Error",
                "status": exc.status_code
            }
        )
    else:
        # Para pÃ¡ginas HTML: mantener comportamiento original
        if exc.status_code in [301, 302, 303, 307, 308]:
            return RedirectResponse(url=exc.headers.get("location", "/login"), status_code=exc.status_code)
        return JSONResponse(status_code=exc.status_code, content={"error": str(exc.detail)})


# âœ… MANEJADOR GLOBAL DE EXCEPCIONES NO MANEJADAS
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Maneja cualquier excepciÃ³n no manejada y devuelve JSON para APIs"""
    import traceback
    
    # Log del error
    print(f"[ERROR] {exc}", file=__import__("sys").stderr)
    traceback.print_exc()
    
    if request.url.path.startswith("/api/"):
        # Para APIs: devolver JSON siempre
        return JSONResponse(
            status_code=500,
            content={
                "error": "Error interno del servidor",
                "detail": str(exc) if os.getenv("DEBUG", "false").lower() == "true" else "Error desconocido"
            }
        )
    else:
        # Para pÃ¡ginas HTML: devolver error genÃ©rico
        return JSONResponse(
            status_code=500,
            content={"error": "Error interno del servidor"}
        )


def login_required(request: Request):
    """Dependency for protecting routes behind a simple session login."""
    user = request.session.get("user")
    if not user:
        # Para APIs: lanzar excepciÃ³n JSON
        if request.url.path.startswith("/api/"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="SesiÃ³n expirada. Por favor login nuevamente."
            )
        else:
            # Para pÃ¡ginas HTML: redirigir a login
            raise HTTPException(status_code=status.HTTP_302_FOUND, headers={"Location": "/login"})
    return user


def login_attempt_key(request: Request, username: str) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    client_ip = forwarded.split(",", 1)[0].strip() if forwarded else ""
    if not client_ip and request.client:
        client_ip = request.client.host
    return f"{client_ip}:{username.strip().lower()}"


def is_login_locked(key: str) -> bool:
    attempt = LOGIN_ATTEMPTS.get(key)
    if not attempt:
        return False
    locked_until = float(attempt.get("locked_until", 0))
    if locked_until and locked_until > time.time():
        return True
    if locked_until:
        LOGIN_ATTEMPTS.pop(key, None)
    return False


def register_failed_login(key: str) -> None:
    now = time.time()
    attempt = LOGIN_ATTEMPTS.get(key, {"count": 0, "first_at": now, "locked_until": 0})
    if now - float(attempt.get("first_at", now)) > LOGIN_LOCK_SECONDS:
        attempt = {"count": 0, "first_at": now, "locked_until": 0}
    attempt["count"] = int(attempt.get("count", 0)) + 1
    if int(attempt["count"]) >= LOGIN_MAX_ATTEMPTS:
        attempt["locked_until"] = now + LOGIN_LOCK_SECONDS
    LOGIN_ATTEMPTS[key] = attempt


@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login", response_class=HTMLResponse)
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """Validate credentials and establish session."""
    key = login_attempt_key(request, username)
    if is_login_locked(key):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Demasiados intentos. Intenta nuevamente en unos minutos."},
            status_code=429,
        )

    expected_password = ADMIN_USERS.get(username)
    if expected_password and secrets.compare_digest(password, expected_password):
        LOGIN_ATTEMPTS.pop(key, None)
        request.session["user"] = username
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    register_failed_login(key)
    # invalid -> re-render with error message
    return templates.TemplateResponse("login.html", {"request": request, "error": "Usuario o contraseÃ±a incorrectos"})


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)


# ðŸ”¹ PÃGINA PRINCIPAL - Escaneo QR unificado
@app.get("/", response_class=HTMLResponse)
def index(request: Request, user: str = Depends(login_required)):
    return templates.TemplateResponse("scan.html", {"request": request})


# ðŸ”¹ PÃGINA DE CONTROL DE PUERTA
@app.get("/puerta", response_class=HTMLResponse)
def puerta_control(request: Request, user: str = Depends(login_required)):
    return templates.TemplateResponse("puerta.html", {"request": request})


# ðŸ”¹ PÃGINA PARA GENERAR CÃ“DIGOS QR
@app.get("/cotizador", response_class=HTMLResponse)
def cotizador_page(request: Request, user: str = Depends(login_required)):
    return templates.TemplateResponse("cotizador.html", {"request": request})

@app.get("/generar-qr", response_class=HTMLResponse)
def generar_qr_page(request: Request, user: str = Depends(login_required)):
    return templates.TemplateResponse("generar_qr.html", {"request": request})


# ðŸ”¹ PÃGINA PARA VER HISTORIAL DE UBICACIONES
@app.get("/historial", response_class=HTMLResponse)
def historial_page(request: Request, user: str = Depends(login_required)):
    return templates.TemplateResponse("historial.html", {"request": request})


@app.get("/reportes-diarios", response_class=HTMLResponse)
def reportes_diarios_page(request: Request, user: str = Depends(login_required)):
    return templates.TemplateResponse("reportes_diarios.html", {"request": request})


# ðŸ”¹ API PARA GENERAR CÃ“DIGO QR (protegido)
@app.post("/api/generar-qr")
def generar_codigo_qr(user: str = Depends(login_required)):
    """Genera un cÃ³digo QR Ãºnico para un vehÃ­culo"""
    import qrcode
    from io import BytesIO
    import base64
    
    # Generar cÃ³digo Ãºnico
    codigo_qr = "veh_" + uuid.uuid4().hex[:8]
    
    # Crear imagen QR (requiere pillow para manipular imÃ¡genes)
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
        "mensaje": f"CÃ³digo QR generado. Imprime o captura esta imagen y pÃ©gala en tu vehÃ­culo."
    }


# ðŸ”¹ LISTAR TODOS LOS VEHÃCULOS REGISTRADOS (protegido)
@app.get("/api/list-vehicles")
def list_vehicles(db: Session = Depends(get_db), user: str = Depends(login_required)):
    """Lista todos los vehÃ­culos registrados con sus cÃ³digos QR"""
    vehicles = db.query(Vehicle).order_by(Vehicle.created_at.desc()).all()
    
    if not vehicles:
        return {
            "total_vehiculos": 0,
            "vehicles": [],
            "mensaje": "No hay vehÃ­culos registrados"
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


# ðŸ”¹ REGENERAR QR PARA UN VEHÃCULO EXISTENTE (Sin perder historial)
@app.get("/api/cotizador/options")
def cotizador_options(user: str = Depends(login_required)):
    return {
        "options": cotizador.get_options_index(),
        "versions": cotizador.get_versions_index(),
        "years": cotizador.get_year_options(),
    }


@app.post("/api/cotizador/quote")
def cotizador_quote(payload: dict, user: str = Depends(login_required)):
    try:
        return cotizador.quote(payload)
    except cotizador.CotizadorError as exc:
        return JSONResponse(status_code=422, content={"error": str(exc)})
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})


@app.get("/api/cotizador/market/{kind}")
def cotizador_market(kind: str, request: Request, user: str = Depends(login_required)):
    if kind not in {"used", "new"}:
        return JSONResponse(status_code=404, content={"error": "Tipo de mercado no valido"})
    return cotizador.market_response(kind, dict(request.query_params))

@app.post("/api/regenerar-qr/{vehicle_code}")
def regenerar_qr_existente(vehicle_code: str, db: Session = Depends(get_db), user: str = Depends(login_required)):
    """Regenera la imagen QR para un vehÃ­culo existente (mantiene el mismo cÃ³digo y historial)"""
    import qrcode
    from io import BytesIO
    import base64
    
    # Limpiar y preparar el cÃ³digo
    vehicle_code = vehicle_code.strip()
    
    # Verificar que el vehÃ­culo existe (case-insensitive)
    vehicle = db.query(Vehicle).filter(Vehicle.code.ilike(vehicle_code)).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail=f"VehÃ­culo no encontrado: {vehicle_code}")
    
    # Regenerar la imagen QR con el MISMO cÃ³digo
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(vehicle_code)  # â† MISMO CÃ“DIGO
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
        "mensaje": f"CÃ³digo QR regenerado para {vehicle.name}. Imprime y reemplaza el papel daÃ±ado. Â¡El historial se mantiene intacto!"
    }


# ðŸ”¹ BUSCAR O CREAR VEHÃCULO POR CÃ“DIGO QR (protegido)
@app.post("/api/vehicle-qr/{vehicle_code}")
def get_or_create_vehicle(vehicle_code: str, db: Session = Depends(get_db), user: str = Depends(login_required)):
    """Busca un vehÃ­culo por cÃ³digo QR. Si existe, retorna sus datos."""
    try:
        vehicle = db.query(Vehicle).filter(Vehicle.code == vehicle_code).first()
        
        if vehicle:
            return {
                "exists": True,
                "vehicle_code": vehicle.code,
                "vehicle_name": vehicle.name,
                "vehicle_id": vehicle.id,
                "origen": vehicle.origen if hasattr(vehicle, 'origen') else None,
                "destino": vehicle.destino if hasattr(vehicle, 'destino') else None,
                "responsable_origen": vehicle.responsable_origen if hasattr(vehicle, 'responsable_origen') else None,
                "responsable_destino": vehicle.responsable_destino if hasattr(vehicle, 'responsable_destino') else None,
                "nivel_gasolina": vehicle.nivel_gasolina if hasattr(vehicle, 'nivel_gasolina') else None,
                "kilometraje": vehicle.kilometraje if hasattr(vehicle, 'kilometraje') else None,
                "observaciones": vehicle.observaciones if hasattr(vehicle, 'observaciones') else None,
            }
        else:
            return {
                "exists": False,
                "vehicle_code": vehicle_code,
                "message": "Nuevo vehÃ­culo - Por favor registra el nombre"
            }
    except Exception as e:
        # Devolver error JSON, no HTML
        return JSONResponse(status_code=500, content={"error": str(e)})


# ðŸ”¹ REGISTRAR NUEVO VEHÃCULO (protegido)
@app.post("/api/register-vehicle")
def register_vehicle(data: VehicleCreate, db: Session = Depends(get_db), user: str = Depends(login_required)):
    """Registra un nuevo vehÃ­culo con el cÃ³digo QR y nombre"""
    try:
        # Verificar si ya existe un vehÃ­culo con ese cÃ³digo
        existing = db.query(Vehicle).filter(Vehicle.code == data.code).first()
        if existing:
            return JSONResponse(status_code=409, content={"error": "Este cÃ³digo QR ya estÃ¡ registrado", "success": False})
        
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
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e), "success": False})


# ðŸ”¹ ACTUALIZAR CAMPOS ADICIONALES DE VEHÃCULO EXISTENTE (protegido)
@app.post("/api/update-vehicle/{vehicle_code}")
def update_vehicle(vehicle_code: str, data: VehicleCreate, db: Session = Depends(get_db), user: str = Depends(login_required)):
    """Los datos de formulario ahora se guardan con cada ubicaciÃ³n, no con el vehÃ­culo"""
    try:
        vehicle = db.query(Vehicle).filter(Vehicle.code == vehicle_code).first()
        if not vehicle:
            return JSONResponse(status_code=404, content={"error": "VehÃ­culo no encontrado", "success": False})
        
        # Solo retornar info del vehÃ­culo
        return {
            "success": True,
            "vehicle_code": vehicle.code,
            "vehicle_name": vehicle.name,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e), "success": False})


# ðŸ”¹ GUARDAR UBICACIÃ“N CON CONFIRMACIÃ“N (protegido)
@app.post("/api/save-location/{vehicle_code}")
def save_location(vehicle_code: str, data: LocationCreate, db: Session = Depends(get_db), user: str = Depends(login_required)):
    """Guarda la ubicaciÃ³n GPS del vehÃ­culo con todos los datos del formulario"""
    vehicle = db.query(Vehicle).filter(Vehicle.code == vehicle_code).first()
    
    if not vehicle:
        raise HTTPException(status_code=404, detail="VehÃ­culo no encontrado")
    
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
        "message": "UbicaciÃ³n guardada correctamente",
        "location_id": location.id,
        "latitude": location.latitude,
        "longitude": location.longitude,
        "timestamp": location.created_at
    }


# ðŸ”¹ OBTENER ÃšLTIMO REGISTRO DE UBICACIÃ“N (protegido)
@app.get("/api/last-location/{vehicle_code}")
def get_last_location(vehicle_code: str, db: Session = Depends(get_db), user: str = Depends(login_required)):
    """Obtiene la Ãºltima ubicaciÃ³n registrada de un vehÃ­culo"""
    vehicle = db.query(Vehicle).filter(Vehicle.code == vehicle_code).first()
    
    if not vehicle:
        raise HTTPException(status_code=404, detail="VehÃ­culo no encontrado")
    
    last_location = (
        db.query(Location)
        .filter(Location.vehicle_id == vehicle.id)
        .order_by(Location.created_at.desc())
        .first()
    )
    
    if not last_location:
        return {"message": "No hay registro de ubicaciÃ³n"}
    
    return {
        "vehicle_name": vehicle.name,
        "latitude": last_location.latitude,
        "longitude": last_location.longitude,
        "timestamp": to_bogota(last_location.created_at)
    }


# ðŸ”¹ OBTENER HISTORIAL COMPLETO DE UBICACIONES POR NOMBRE O CÃ“DIGO
@app.get("/api/historial/nombre/{vehicle_name}")
def get_historial_por_nombre(vehicle_name: str, db: Session = Depends(get_db), user: str = Depends(login_required)):
    """Busca un vehÃ­culo por nombre O por cÃ³digo QR y retorna su historial"""
    vehicle = None
    
    # Primero intenta buscar por nombre (case-insensitive)
    vehicle = (
        db.query(Vehicle)
        .filter(Vehicle.name.ilike(f"%{vehicle_name}%"))
        .first()
    )
    
    # Si no encuentra por nombre, intenta por cÃ³digo QR
    if not vehicle:
        vehicle = (
            db.query(Vehicle)
            .filter(Vehicle.code.ilike(f"%{vehicle_name}%"))
            .first()
        )
    
    if not vehicle:
        raise HTTPException(status_code=404, detail="VehÃ­culo no encontrado")
    
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
            "message": "No hay registros de ubicaciÃ³n"
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


# ðŸ”¹ OBTENER HISTORIAL POR CÃ“DIGO QR (para dashboard)
@app.get("/api/historial/{vehicle_code}")
def get_historial_por_codigo(vehicle_code: str, db: Session = Depends(get_db), user: str = Depends(login_required)):
    """Obtiene el historial de ubicaciones de un vehÃ­culo por su cÃ³digo QR"""
    vehicle = db.query(Vehicle).filter(Vehicle.code == vehicle_code).first()
    
    if not vehicle:
        raise HTTPException(status_code=404, detail="VehÃ­culo no encontrado")
    
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
            "message": "No hay registros de ubicaciÃ³n"
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


# ðŸ”¹ GUARDAR UBICACIÃ“N MANUALMENTE (desde dashboard)
@app.post("/api/guardar-ubicacion")
def guardar_ubicacion_manual(data: dict, db: Session = Depends(get_db), user: str = Depends(login_required)):
    """Guarda manualmente una ubicaciÃ³n con el botÃ³n 'Guardar UbicaciÃ³n'"""
    vehicle_code = data.get("vehicle_code")
    latitude = data.get("latitude")
    longitude = data.get("longitude")
    
    if not vehicle_code or latitude is None or longitude is None:
        return {"success": False, "error": "Datos incompletos"}
    
    vehicle = db.query(Vehicle).filter(Vehicle.code == vehicle_code).first()
    
    if not vehicle:
        return {"success": False, "error": "VehÃ­culo no encontrado"}
    
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
        "message": "UbicaciÃ³n guardada correctamente",
        "location_id": location.id,
        "latitude": location.latitude,
        "longitude": location.longitude,
        "timestamp": to_bogota(location.created_at)
    }


# ðŸ”¹ EXPORTAR A EXCEL CON FILTROS
@app.get("/api/export-excel")
def export_excel(
    vehicle_code: str = None,
    date_from: str = None,
    date_to: str = None,
    db: Session = Depends(get_db),
    user: str = Depends(login_required)
):
    """Exporta registros de ubicaciÃ³n a Excel con filtros de fecha y placa"""
    
    # ConstrucciÃ³n de query base
    query = db.query(Location).join(Vehicle)
    
    # Filtro por placa (vehÃ­culo) - requerido
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
            raise HTTPException(status_code=400, detail="Formato de date_from invÃ¡lido (use YYYY-MM-DD)")
    
    if date_to:
        try:
            date_to_dt = datetime.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
            query = query.filter(Location.created_at <= date_to_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de date_to invÃ¡lido (use YYYY-MM-DD)")
    
    locations = query.order_by(Location.created_at.desc()).all()
    
    if not locations:
        raise HTTPException(status_code=404, detail="No hay registros que coincidan con los filtros")
    
    # Construir datos para Excel
    data = []
    for idx, loc in enumerate(locations, 1):
        data.append({
            "#": idx,
            "Fecha y Hora": to_bogota(loc.created_at).strftime("%d/%m/%Y %H:%M:%S"),
            "CÃ³digo": loc.vehicle.code,
            "VehÃ­culo": loc.vehicle.name,
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


# ðŸ”¹ DASHBOARD - Ver historial del vehÃ­culo
@app.get("/dashboard/{vehicle_code}", response_class=HTMLResponse)
def dashboard(request: Request, vehicle_code: str, db: Session = Depends(get_db), user: str = Depends(login_required)):
    vehicle = db.query(Vehicle).filter(Vehicle.code == vehicle_code).first()
    
    if not vehicle:
        return HTMLResponse("VehÃ­culo no encontrado", status_code=404)
    
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


# ðŸ”¹ VERIFICAR SI UN VEHÃCULO FUE ESCANEADO HOY
@app.get("/api/check-vehicle-scan/{vehicle_code}")
def check_vehicle_scan(vehicle_code: str, db: Session = Depends(get_db), user: str = Depends(login_required)):
    """
    Verifica si un vehÃ­culo fue escaneado HOY
    - Busca por cÃ³digo interno (veh_xxx) O por placa (NHQ928, etc)
    - Si fue escaneado: Retorna info del escaneo
    - Si NO fue escaneado: Permite registrarlo como no escaneado
    """
    from datetime import datetime, timedelta
    
    # Busca por cÃ³digo interno O por placa (name)
    vehicle = db.query(Vehicle).filter(
        (Vehicle.code == vehicle_code) | (Vehicle.name == vehicle_code)
    ).first()
    
    if not vehicle:
        return {
            "found": False,
            "message": "VehÃ­culo no encontrado"
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
        # SÃ FUE ESCANEADO HOY
        return {
            "found": True,
            "was_scanned": True,
            "vehicle_code": vehicle.code,
            "vehicle_name": vehicle.name,
            "scanned_at": to_bogota(today_scan.created_at).strftime("%H:%M:%S"),
            "location": today_scan.direccion_completa or "UbicaciÃ³n no disponible",
            "responsable": today_scan.responsable_origen or "No registrado",
            "message": f"âœ… {vehicle.name} fue escaneado a las {to_bogota(today_scan.created_at).strftime('%H:%M:%S')}"
        }
    else:
        # NO FUE ESCANEADO HOY
        return {
            "found": True,
            "was_scanned": False,
            "vehicle_code": vehicle.code,
            "vehicle_name": vehicle.name,
            "message": f"âŒ {vehicle.name} NO fue escaneado hoy",
            "can_mark_unscanned": True
        }


# ðŸ”¹ MARCAR VEHÃCULO COMO NO ESCANEADO
@app.post("/api/mark-unscanned/{vehicle_code}")
def mark_vehicle_unscanned(
    vehicle_code: str,
    data: UnscannedVehicleCreate,
    db: Session = Depends(get_db),
    user: str = Depends(login_required)
):
    """
    Registra que un vehÃ­culo NO fue escaneado por su placa (name)
    - responsable_esperado: QuiÃ©n DEBERÃA haber escaneado (nombre del movilizador)
    - motivo: RazÃ³n por la que no fue escaneado (opcional)
    """
    vehicle = db.query(Vehicle).filter(Vehicle.name == vehicle_code).first()
    
    if not vehicle:
        raise HTTPException(status_code=404, detail="VehÃ­culo no encontrado")
    
    # Crear registro de no escaneado
    unscanned = UnscannedVehicle(
        vehicle_id=vehicle.id,
        responsable_esperado=data.responsable_esperado,
        verificado_por=user,  # QuiÃ©n registra (persona en puerta)
        motivo=data.motivo
    )
    
    db.add(unscanned)
    db.commit()
    db.refresh(unscanned)
    
    return {
        "success": True,
        "message": f"âœ— {vehicle.name} registrado como NO escaneado",
        "vehicle_code": vehicle.code,
        "vehicle_name": vehicle.name,
        "responsable_esperado": data.responsable_esperado,
        "verified_by": user,
        "timestamp": to_bogota(unscanned.created_at).strftime("%d/%m/%Y %H:%M:%S")
    }


# ðŸ”¹ OBTENER LISTA DE VEHÃCULOS NO ESCANEADOS HOY
@app.get("/api/unscanned-today")
def get_unscanned_today(db: Session = Depends(get_db), user: str = Depends(login_required)):
    """
    Retorna lista de vehÃ­culos que NO fueron escaneados hoy
    Ãštil para REPORTE de incumplimientos
    """
    from datetime import datetime
    
    today = datetime.now(tz=bogota_tz).date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    # VehÃ­culos no escaneados HOY
    unscanned_today = db.query(UnscannedVehicle)\
        .join(Vehicle)\
        .filter(UnscannedVehicle.created_at >= today_start)\
        .filter(UnscannedVehicle.created_at <= today_end)\
        .order_by(UnscannedVehicle.created_at.desc())\
        .all()
    
    # Total de vehÃ­culos registrados
    total_vehicles = db.query(Vehicle).count()
    
    # VehÃ­culos escaneados hoy
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


# ðŸ”¹ OBTENER REPORTE COMPLETO DEL DÃA
@app.get("/api/report-daily")
def get_daily_report(db: Session = Depends(get_db), user: str = Depends(login_required)):
    """
    Reporte completo del dÃ­a: QuÃ© vehÃ­culos salieron, cuÃ¡les no fueron escaneados, etc.
    """
    from datetime import datetime
    
    today = datetime.now(tz=bogota_tz).date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    # Todos los vehÃ­culos
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


# ðŸ”¹ BUSCAR VEHÃCULOS NO ESCANEADOS CON FILTROS
@app.get("/api/search-unscanned")
def search_unscanned(
    responsable: str = None,
    vehicle_code: str = None,
    vehicle_name: str = None,
    db: Session = Depends(get_db),
    user: str = Depends(login_required)
):
    """
    Busca vehÃ­culos NO escaneados hoy con filtros:
    - responsable: Nombre del responsable (bÃºsqueda parcial)
    - vehicle_code: CÃ³digo del vehÃ­culo
    - vehicle_name: Nombre/placa del vehÃ­culo (bÃºsqueda parcial)
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


# ðŸ”¹ EXPORTAR A EXCEL - VEHÃCULOS NO ESCANEADOS
@app.get("/api/export-unscanned-excel")
def export_unscanned_excel(
    db: Session = Depends(get_db),
    user: str = Depends(login_required)
):
    """
    Exporta a Excel los vehÃ­culos NO escaneados de hoy
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
            "Placa/CÃ³digo": u.vehicle.code,
            "Nombre VehÃ­culo": u.vehicle.name,
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


# ðŸ”¹ EXPORTAR A EXCEL - TODOS (ESCANEADOS + NO ESCANEADOS)
@app.get("/api/export-daily-report-excel")
def export_daily_report_excel(
    db: Session = Depends(get_db),
    user: str = Depends(login_required)
):
    """
    Exporta completo el reporte del dÃ­a a Excel
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
                "Placa/CÃ³digo": vehicle.code,
                "Nombre": vehicle.name,
                "Estado": "âœ… ESCANEADO",
                "Hora": to_bogota(today_scan.created_at).strftime("%H:%M:%S"),
                "Responsable": today_scan.responsable_origen or "No registrado",
                "UbicaciÃ³n": today_scan.direccion_completa or "No disponible",
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
                    "Placa/CÃ³digo": vehicle.code,
                    "Nombre": vehicle.name,
                    "Estado": "âŒ NO ESCANEADO",
                    "Hora": to_bogota(unscanned_record.created_at).strftime("%H:%M:%S"),
                    "Responsable": unscanned_record.responsable_esperado or "No registrado",
                    "UbicaciÃ³n": "-",
                    "Motivo": unscanned_record.motivo or "-"
                })
            else:
                data.append({
                    "Placa/CÃ³digo": vehicle.code,
                    "Nombre": vehicle.name,
                    "Estado": "âš ï¸ SIN REGISTRO",
                    "Hora": "-",
                    "Responsable": "-",
                    "UbicaciÃ³n": "-",
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


# ðŸ”¹ OBTENER ESCANEOS POR FECHA ESPECÃFICA
@app.get("/api/escaneos-por-fecha")
def get_escaneos_por_fecha(
    fecha: str,  # Formato: YYYY-MM-DD
    db: Session = Depends(get_db),
    user: str = Depends(login_required)
):
    """
    Obtiene todos los escaneos de una fecha especÃ­fica con la informaciÃ³n del vehÃ­culo
    Retorna: lista de vehÃ­culos escaneados ese dÃ­a con placa y responsables
    """
    from datetime import datetime as dt
    
    try:
        # Parsear la fecha
        fecha_obj = dt.strptime(fecha, "%Y-%m-%d").date()
        
        # Crear rango de tiempo para ese dÃ­a (00:00:00 a 23:59:59)
        hora_inicio = dt.combine(fecha_obj, dt.min.time()).replace(tzinfo=bogota_tz)
        hora_fin = dt.combine(fecha_obj, dt.max.time()).replace(tzinfo=bogota_tz)
        
        # Obtener todos los vehÃ­culos
        todos_vehiculos = db.query(Vehicle).all()
        
        escaneos = []
        no_escaneados = []
        vehiculos_con_escaneos = set()  # Para contar vehÃ­culos Ãºnicos escaneados
        
        for vehiculo in todos_vehiculos:
            # Buscar el ÃšLTIMO escaneo del vehÃ­culo ese dÃ­a (evita duplicados)
            escaneos_dia = (
                db.query(Location)
                .filter(Location.vehicle_id == vehiculo.id)
                .filter(Location.created_at >= hora_inicio)
                .filter(Location.created_at <= hora_fin)
                .order_by(Location.created_at.desc())  # Ordenar por fecha descendente
                .all()
            )
            
            if escaneos_dia:
                vehiculos_con_escaneos.add(vehiculo.id)  # Marcar que este vehÃ­culo fue escaneado
                # Solo usar el ÃšLTIMO escaneo (el primero de la lista descendente)
                escaneo = escaneos_dia[0]
                total_escaneos = len(escaneos_dia)
                
                # Saltar si el Ãºltimo escaneo no tiene datos importantes (es un duplicado vacÃ­o)
                # Buscar el primer escaneo que tenga datos
                mejor_escaneo = escaneo
                for e in escaneos_dia:
                    if e.responsable_origen or e.origen or e.destino or e.responsable_destino:
                        mejor_escaneo = e
                        break
                
                escaneos.append({
                    "id": mejor_escaneo.id,
                    "placa": vehiculo.code,
                    "nombre_vehiculo": vehiculo.name,
                    "num_escaneo": 1,  # Solo mostramos 1 por vehÃ­culo
                    "total_escaneos": total_escaneos,  # Pero indicamos cuÃ¡ntos hay
                    "hora_escaneo": to_bogota(mejor_escaneo.created_at).strftime("%d/%m/%Y %H:%M:%S"),
                    "responsable_origen": mejor_escaneo.responsable_origen or "No registrado",
                    "responsable_destino": mejor_escaneo.responsable_destino or "No registrado",
                    "origen": mejor_escaneo.origen or "-",
                    "destino": mejor_escaneo.destino or "-",
                    "nivel_gasolina": mejor_escaneo.nivel_gasolina or "-",
                    "kilometraje": mejor_escaneo.kilometraje or "-",
                    "observaciones": mejor_escaneo.observaciones or "-",
                    "direccion": mejor_escaneo.direccion_completa or "No disponible",
                    "latitude": mejor_escaneo.latitude,
                    "longitude": mejor_escaneo.longitude
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
                "escaneados": len(vehiculos_con_escaneos),  # VehÃ­culos Ãºnicos escaneados
                "total_movimientos": len(escaneos),  # Total de escaneos (puede ser > escaneados)
                "no_escaneados": len(no_escaneados),
                "sin_registro": len(todos_vehiculos) - len(vehiculos_con_escaneos) - len(no_escaneados),
                "tasa_cumplimiento": round((len(vehiculos_con_escaneos) / len(todos_vehiculos) * 100), 2) if len(todos_vehiculos) > 0 else 0
            },
            "escaneos": escaneos,
            "no_escaneados": no_escaneados
        }
    
    except ValueError:
        return {
            "success": False,
            "error": "Formato de fecha invÃ¡lido. Use YYYY-MM-DD (ej: 2026-03-27)"
        }


