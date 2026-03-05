# 📋 Resumen de Correcciones de Seguridad

La aplicación ha sido completamente actualizada con sistemas de seguridad robustos. Aquí te mostramos exactamente qué cambió.

---

## ✅ Protecciones implementadas

### 1. **Login obligatorio** 🔐
- Todas las rutas principales (`/`, `/generar-qr`, `/historial`) y endpoints de API requieren autenticación.
- Se creó una página de login (`/login`) con formulario de usuario y contraseña.
- Las credenciales se validan de forma segura usando `secrets.compare_digest()` (evita timing attacks).

### 2. **Gestión de sesiones** 🎫
- Se agregó `SessionMiddleware` de Starlette para mantener sesiones seguras.
- Cada usuario autenticado recibe una cookie de sesión firmada con un secreto.
- Al cerrar sesión,  la cookie se limpia automáticamente.

### 3. **CORS cerrado** 🚫
- Antes: `allow_origins=["*"]` (cualquiera podía llamar a tu API)
- Ahora: Solo orígenes explícitos definidos en `ALLOWED_ORIGINS` (variable `.env`)
- Esto evita que otros sitios web hagan peticiones a tu API.

### 4. **Variables de entorno de seguridad** 📝
Se requieren 4 nuevas variables en el archivo `.env`:

```env
ADMIN_USER=admin                    # nombre de usuario
ADMIN_PASS=secret                   # contraseña (cámbiala!)
SESSION_SECRET=frase_secreta_larga  # para firmar sesiones (mín. 20 caracteres)
ALLOWED_ORIGINS=http://localhost:8001  # dominios permitidos
```

### 5. **Sin exposición de IP** 🌐
- Antes: Tu IP era visible en algunas peticiones al acceder desde el móvil
- Ahora: Solo se usan códigos QR internos (`veh_abc123`), no expones tu dirección

---

## 📁 Archivos modificados

| Archivo | Cambios |
|---------|---------|
| **app/main.py** | ✅ Login `POST /login`, logout `GET /logout`, dependencies de autenticación |
| **templates/login.html** | ✅ **Nuevo** - Página de login con formulario |
| **templates/scan.html** | ✅ Info de usuario + botón logout en esquina |
| **templates/historial.html** | ✅ Info de usuario + botón logout en esquina |
| **templates/generar_qr.html** | ✅ Info de usuario + botón logout en esquina |
| **.env.example** | ✅ Actualizado con variables de seguridad |
| **requirements.txt** | ✅ Agregado: `starlette` |
| **docker-compose.yml** | ✅ Variables de seguridad en configuración |
| **SEGURIDAD.md** | ✅ **Nuevo** - Documentación detallada de cambios |

---

## 🚀 CÓMO USAR AHORA

### Paso 1: Preparar el .env
Crea un archivo `.env` en la raíz del proyecto (o copia `.env.example` y modifícalo):

```bash
# Windows PowerShell
Copy-Item .env.example .env

# Luego edita .env con valores seguros
```

**Contenido mínimo:**
```
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432
DB_NAME=codigoqr_db
ADMIN_USER=tu_usuario
ADMIN_PASS=tu_contrasena_segura
SESSION_SECRET=un_texto_largo_y_aleatorio_minimo_20_caracteres
ALLOWED_ORIGINS=http://localhost:8001
```

### Paso 2: Instalar dependencias nuevas
```bash
pip install -r requirements.txt
```

### Paso 3: Ejecutar la aplicación

**Con Docker Compose:**
```bash
docker-compose up
# Accede a: http://localhost:8001
```

**Local con Python:**
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
# Accede a: http://localhost:8001
```

### Paso 4: Iniciar sesión
1. Verás la página de login automáticamente.
2. Ingresa las credenciales del `.env`:
   - Usuario: `tu_usuario`
   - Contraseña: `tu_contrasena_segura`
3. ¡Listo! Acceso concedido al sistema.

---

## 🔒 Para acceder desde otro dispositivo (móvil con ngrok)

Aunque ahora está más seguro con login, **aún así no es lo más seguro** usar ngrok directamente. Aquí están las opciones:

### Opción A: **Mejor (Recomendado)**
Desplega en un servidor con HTTPS:
- Heroku (con Let's Encrypt)
- AWS/Azure con certificado SSL
- Digital Ocean
- Nube de tu choice

### Opción B: ngrok + login (lo que tienes ahora)
1. Inicia ngrok: `ngrok http 8001`
2. Copias tu URL de ngrok (ej: `https://abc123.ngrok.io`)
3. Actualizas `.env`:
   ```
   ALLOWED_ORIGINS=https://abc123.ngrok.io,http://localhost:8001
   ```
4. Desde el móvil: van a `https://abc123.ngrok.io` → login → acceso.

### Opción C: Restringir a red local
Si solo accedes desde dispositivos en tu red local:
```
ALLOWED_ORIGINS=http://192.168.1.100:8001,http://localhost:8001
```

---

## 🛡️ Cambios invisibles al usuario (pero importantes)

- ✅ Comparación de contraseña con `secrets.compare_digest()` (evita timing attacks)
- ✅ Sesiones firmadas criptográficamente
- ✅ Middleware CORS restringido
- ✅ Todas las rutas protegidas con `Depends(login_required)`
- ✅ Redireccionamiento automático a login si se intenta acceso sin autenticación

---

## ⚠️ Limitaciones y pasos futuros

**Limitaciones actuales:**
- Login por sesión de cookie (simple pero limitado)
- No hay 2FA (autenticación de dos factores)
- Un solo usuario admin (no multiusuario)

**Para la próxima fase (opcional):**
- JWT tokens en lugar de sesiones (mejor para apps móviles)
- 2FA con QR/app autenticador
- Múltiples usuarios con roles (admin, usuario básico, etc.)
- Rate limiting en login (proteger contra fuerza bruta)
- Logs de auditoría

---

## 🧪 Probar sin problemas

### En tu PC (localhost)
```bash
# Terminal 1: Levanta la app
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001

# Terminal 2: Abre en navegador
http://localhost:8001
# Login con las credenciales del .env
# ✅ Acceso concedido
```

### Desde el móvil (misma red)
```
1. Encuentra tu IP de PC: ipconfig (busca IPv4)
2. En móvil: http://192.168.X.X:8001
3. Verás login → ingresa credenciales
4. ✅ Acceso concedido
```

---

## 📞 Si algo falla

**Error: "El usuario o contraseña son incorrectos"**
- Verifica que coincidan exactamente los valores en `.env`

**Error: "No se puede conectar"**
- Verifica que la app está levantada: `uvicorn app.main:app --reload`
- Comprueba el puerto: ¿8001?

**Error: "SessionMiddleware not found"**
- Instala starlette: `pip install starlette`

**Error: CORS bloqueado**
- Asegúrate de que tu origen (URL del navegador) está en `ALLOWED_ORIGINS`

---

## 📖 Documentación completa

Lee **`SEGURIDAD.md`** para detalles técnicos profundos sobre:
- Flujo de autenticación completo
- Variables de entorno
- Cómo desplegar en producción
- Recomendaciones de hardening
- Ejemplos de rate limiting y logs
- Opciones futuras (OAuth2, JWT, etc de)

---

**¡Tu aplicación está protegida! 🎉**

Ahora nadie puede acceder sin credenciales válidas, y tus datos están más seguros.
