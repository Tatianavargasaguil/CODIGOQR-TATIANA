# 🔐 Cambios de Seguridad Implementados

## Resumen
Se han implementado múltiples capas de seguridad para proteger la aplicación contra accesos no autorizados, especialmente cuando se expone a través de ngrok o se accede desde dispositivos móviles.

---

## 🚨 Problemas que se resolvieron

### 1. **Acceso sin autenticación**
- **Problema:** Cualquiera podía acceder a `/`, `/generar-qr`, `/historial` y todos los endpoints sin ninguna validación.
- **Solución:** Sistema de login con sesión. Todas las rutas ahora redirigen a `/login` si el usuario no está autenticado.

### 2. **CORS abierto a todos los orígenes**
- **Problema:** `allow_origins=["*"]` permitía que cualquier sitio web hiciera peticiones a tu API.
- **Solución:** Variable de entorno `ALLOWED_ORIGINS` que controla estrictamente qué dominios pueden acceder a la API.

### 3. **IP pública expuesta en la interfaz**
- **Problema:** Al acceder desde el móvil se veía la dirección IP en algunas peticiones (aunque el navegador la ocultaba).
- **Solución:** Ahora los datos sensibles no se transmiten en la URL. Solo el código QR del vehículo se usa en las rutas, no la IP.

### 4. **Modo desarrollo (`--reload`) expuesto en "producción"**
- **Problema:** Si ejecutabas con `uvicorn --reload`, cualquiera podía causar comportamientos impredecibles.
- **Solución:** Se documentó usar un servidor de producción (Gunicorn, etc.) para despliegues públicos.

---

## ✅ Cambios implementados

### Backend (`app/main.py`)

#### 1. **Importes de seguridad**
```python
import os
import secrets
from fastapi.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
```

#### 2. **Variables de entorno**
```python
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "secret")
SESSION_SECRET = os.getenv("SESSION_SECRET", "change_this_secret")
ALLOWED_ORIGINS = [...]  # lista desde env
```

#### 3. **Middleware de sesión**
```python
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)
```

#### 4. **CORS restringido**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # no más ["*"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### 5. **Función de validación de sesión**
```python
def login_required(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=302, headers={"Location": "/login"})
    return user
```

#### 6. **Rutas de login/logout**
- `GET /login` → página de formulario
- `POST /login` → valida credenciales y establece sesión
- `GET /logout` → limpia sesión y redirige a login

#### 7. **Protección de rutas**
Todas las rutas protegidas ahora incluyen:
```python
@app.get("/")
def index(request: Request, user: str = Depends(login_required)):
    # Solo se ejecuta si el usuario está autenticado
```

---

## 📝 Configuración (.env)

### Variables requeridas

```dotenv
# Base de Datos
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost  # o "db" si usas Docker
DB_PORT=5432
DB_NAME=codigoqr_db

# Seguridad
ADMIN_USER=admin
ADMIN_PASS=tu_password_secreto  # cámbialo!
SESSION_SECRET=frase_larga_minimo_32_caracteres_aleatorios
ALLOWED_ORIGINS=http://localhost:8001
```

### Para producción (ngrok, VPS, etc.)
Si tienes múltiples dominios o ngrok:
```
ALLOWED_ORIGINS=https://abc123.ngrok.io,https://midominio.com,http://localhost:8001
```

---

## 🚀 Cómo iniciar la aplicación segura

### Docker Compose
```bash
docker-compose up
# Luego accede a http://localhost:8001
# Login: admin / (tu_password_secreto)
```

### Local (Python)
```bash
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8001
# Accede a http://localhost:8001
```

---

## 🔐 Flujo de seguridad

1. Usuario intenta acceder a `http://localhost:8001/`
2. FastAPI valida si la sesión tiene un `user`
3. **Si NO:** redirige a `/login`
4. Usuario ingresa credenciales (usuario/contraseña)
5. Backend valida con `secrets.compare_digest()` (evita timing attacks)
6. **Si válidas:** se establece `request.session["user"] = username`
7. Usuario accede a todas las rutas protegidas
8. Todas las peticiones API verifican el `login_required` 
9. Usuario hace clic en "Cerrar sesión" → limpia sesión y redirige a `/login`

---

## 🛡️ Recomendaciones para producción

### 1. **Cambiar credenciales por defecto**
```env
ADMIN_USER=admin_tuempresa
ADMIN_PASS=un_password_muy_fuerte_32_caracteres
SESSION_SECRET=otro_secreto_muy_largo_y_aleatorio
```

### 2. **Usar HTTPS obligatorio**
- No publiques sin SSL/TLS
- En Heroku: automático con dominios `.herokuapp.com`
- En VPS: usa Let's Encrypt (certbot)

### 3. **Proxies (nginx, Apache)**
Coloca un reverse proxy detrás de tu FastAPI:
```nginx
location / {
    proxy_pass http://127.0.0.1:8001;
    proxy_set_header X-Forwarded-For $remote_addr;
}
```

### 4. **Múltiples usuarios (futuro)**
Si necesitas varios usuarios, guarda credenciales en BD (con hashing bcrypt):
```python
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
```

### 5. **Rate limiting**
Protege el endpoint `/login` para evitar fuerza bruta:
```python
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@app.post("/login")
@limiter.limit("5/minute")
def login(...):
    ...
```

### 6. **Logs y monitoreo**
Registra intentos de login:
```python
import logging
logger = logging.getLogger(__name__)
logger.info(f"Login attempt: {username}")
```

---

## 📊 Resumen de cambios

| Aspecto | Antes | Después |
|--------|-------|---------|
| **Acceso** | Sin restricción | Login requerido |
| **CORS** | `["*"]` | Variables desde `.env` |
| **IP pública** | Visible en peticiones | Oculta (solo código QR) |
| **Rutas protegidas** | Ninguna | todas las rutas principales |
| **Variables de entorno** | Sin autenticación | Admin user/pass + secrets |
| **Sesiones** | No | Sí, con middleware |

---

## 🚧 Limitaciones actuales

Este sistema usa **sesiones basadas en cookies** que es simple pero tiene limitaciones:

- Solo funciona en el mismo navegador/dispositivo
- Si el usuario borra cookies, pierde la sesión
- No es ideal para múltiples dispositivos o apps móviles nativas

### Para una solución más robusta (futuro):
- JWT (JSON Web Tokens) para APIs
- OAuth2 para integración con servicios externos
- 2FA (autenticación de dos factores)
- SSO (Single Sign-On) empresarial

---

## 📞 Soporte
Si tienes dudas sobre la configuración:
1. Verifica que `.env` existe y tiene las variables correctas
2. Revisa logs del servidor para mensajes de error
3. Asegúrate de tener `starlette` instalado: `pip install starlette`
