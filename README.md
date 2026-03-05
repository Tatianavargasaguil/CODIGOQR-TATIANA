# Sistema de Ubicación de Vehículos con Código QR

## 📋 Descripción

Sistema refactorizado que permite:

✅ Escanear código QR pegado en el vehículo
✅ Registrar nuevo vehículo (nombre/placa) si es la primera vez
✅ Capturar ubicación GPS automáticamente
✅ Confirmar ubicación con botón "Buscar Ubicación"
✅ Ver mapa en tiempo real
✅ Guardar histórico de ubicaciones en BD
✅ Dashboard para ver última ubicación del vehículo

## 🏗️ Estructura del Proyecto

```
codigoqr tatiana/
├── app/
│   ├── main.py              # API FastAPI refactorizada
│   ├── models.py            # Modelos SQLAlchemy (Vehicle, Location)
│   ├── schemas.py           # Esquemas Pydantic actualizados
│   ├── db.py                # Configuración de BD
│   └── routes/              # Rutas (vacías, lógica en main.py)
├── templates/
│   ├── scan.html            # ✨ NUEVA interfaz unificada
│   └── dashboard.html       # Dashboard mejorado
├── requirements.txt         # Dependencias Python
├── Dockerfile               # Configuración Docker
└── docker-compose.yml       # Orquestación de contenedores
```

## 🔄 Flujo de Uso

### 1️⃣ **Página Principal** (`/`)
   - Escanea el código QR del vehículo
   - O ingresa el código manualmente

### 2️⃣ **Registro de Vehículo** (si es nuevo)
   - Se muestra formulario para registrar nombre/placa
   - Se guarda con el código QR

### 3️⃣ **Captura de Ubicación**
   - Se obtiene automáticamente la ubicación GPS
   - Se muestra en mapa de Leaflet
   - Se visualizan las coordenadas exactas

### 4️⃣ **Confirmación**
   - Botón "🔍 Buscar Ubicación" para confirmar
   - Muestra resumen con todos los datos
   - Se guarda en la base de datos

### 5️⃣ **Dashboard**
   - Ver última ubicación del vehículo
   - Historial de ubicaciones
   - Mapa con marcador

## 🚀 Instalación y Ejecución

### 🔐 Seguridad adicional
Antes de levantar el servicio es **obligatorio** protegerlo con credenciales y cerrar orígenes CORS. Crea un archivo `.env` y añade estas variables:

```
DB_USER=postgres
DB_PASSWORD=tu_contraseña
DB_HOST=db
DB_PORT=5432
DB_NAME=codigoqr_db
ADMIN_USER=admin         # nombre de usuario del administrador
ADMIN_PASS=secret        # contraseña segura
SESSION_SECRET=frase_larga_y_secreta
ALLOWED_ORIGINS=http://localhost:8001    # dominios permitidos (coma separada)
```

⚠️ Nunca compartas `ADMIN_PASS` ni `SESSION_SECRET` públicamente.

### Opción 1: Con Docker Compose (Recomendado)

```bash
# después de configurar .env

docker-compose up
```

La aplicación quedará accesible en `http://localhost:8001` y mostrará una pantalla de login.

### Opción 2: Local con Python

```bash
# 1. Crear entorno virtual
python -m venv venv
.\venv\Scripts\Activate.ps1

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno (igual al ejemplo anterior)

# 4. Ejecutar aplicación
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

> 📎 Si necesitas acceder desde un dispositivo móvil en la misma red, considera desplegar en un servidor o usar ngrok **con autenticación**. Nunca publiques tu IP pública sin protección.

## 📡 Endpoints API

### Información de Vehículos

- **POST** `/api/vehicle-qr/{vehicle_code}` - Buscar o verificar vehículo por QR
- **POST** `/api/register-vehicle` - Registrar nuevo vehículo
- **POST** `/api/save-location/{vehicle_code}` - Guardar ubicación
- **GET** `/api/last-location/{vehicle_code}` - Obtener última ubicación

### Páginas

- **GET** `/` - Página principal con escáner QR
- **GET** `/dashboard/{vehicle_code}` - Dashboard del vehículo

## 🛠️ Cambios Realizados

### Backend (main.py)
- ✅ Refactorizado flujo de escaneo QR
- ✅ Separación de lógica: buscar vs registrar vehículo
- ✅ Endpoints para confirmación de ubicación
- ✅ Agregado CORS para frontend
- ✅ Manejo mejorado de errores

### Frontend (scan.html)
- ✨ **Interfaz unificada** con múltiples secciones:
  1. Escáner QR (con librería html5-qrcode)
  2. Registro de nuevo vehículo
  3. Captura y visualización de ubicación GPS
  4. Confirmación y resumen final
  
- ✨ Mapa interactivo con Leaflet
- ✨ Diseño moderno y responsivo
- ✨ Estados visuales (cargando, éxito, error)
- ✨ Entrada manual de código QR como fallback

### Dashboard (dashboard.html)
- ✅ Diseño mejorado y consistente
- ✅ Información clara de ubicación
- ✅ Mapa interactivo
- ✅ Botones de acción

### Esquemas (schemas.py)
- ✅ Agregado VehicleCreate
- ✅ Agregado VehicleResponse

## 📦 Dependencias

```
fastapi          # Framework Web
uvicorn          # Servidor ASGI
SQLAlchemy       # ORM
psycopg2-binary  # Driver PostgreSQL
python-dotenv    # Variables de entorno
Jinja2           # Plantillas HTML
qrcode           # Generación de QR
pillow           # Dependencia de imágenes para qrcode
```

Para el frontend:
- **html5-qrcode**: Escáner de QR en navegador
- **Leaflet**: Mapas interactivos
- **OpenStreetMap**: Tiles del mapa

## 🔐 Configuración de Seguridad

Asegúrate de configurar en producción:
- Cambiar CORS origins específicos
- Usar HTTPS
- Validar los códigos QR
- Agregar autenticación si es necesario

## 📍 Características de Geolocalización

- ✅ Requiere HTTPS en producción
- ✅ Solicita permiso del usuario
- ✅ Funciona en navegadores modernos
- ✅ Precisión: ±5-10 metros (varía según dispositivo)

## 🐛 Troubleshooting

**Error: "Cámara no disponible"**
- Verifica permisos de cámara en el navegador
- Usa la entrada manual del código QR

**Error: "Ubicación no disponible"**
- Habilita geolocalización en el navegador
- Asegúrate de usar HTTPS
- Algunos navegadores requieren contexto seguro

**BD no se conecta**
- Verifica archivo .env
- Comprueba que PostgreSQL está en ejecución
- En Docker: revisa logs con `docker-compose logs db`

## 🚀 Próximos Pasos (Opcional)

- [ ] Agregar historial completo de ubicaciones por vehículo
- [ ] Exportar datos a CSV
- [ ] Múltiples usuarios/acceso
- [ ] Notificaciones en tiempo real
- [ ] Geofencing (alertas por zona)
- [ ] Móvil app nativa

---

**¡Tu sistema está listo!** Accede a `http://localhost:8001` 🎉
