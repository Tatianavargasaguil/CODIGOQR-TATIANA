# ⚡ Guía Rápida: Ejecutar la aplicación segura

## 🚀 Inicio rápido (5 minutos)

### 1️⃣ Preparar variables de entorno

Crea un archivo `.env` en la raíz del proyecto:

```env
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432
DB_NAME=codigoqr_db
ADMIN_USER=admin
ADMIN_PASS=tu_password_secreto
SESSION_SECRET=un_secreto_muy_largo_minimo_20_caracteres
ALLOWED_ORIGINS=http://localhost:8001
```

💾 **Guárdalo en:** `C:\codigoqr tatiana\.env`

### 2️⃣ Con Docker Compose (RECOMENDADO)

```bash
# En PowerShell, desde C:\codigoqr tatiana
docker-compose up
```

Espera 30 segundos y accede a: **http://localhost:8001**

**Login:**
- Usuario: `admin`
- Contraseña: `tu_password_secreto`

### 3️⃣ Sin Docker (Python local)

```bash
# Terminal en C:\codigoqr tatiana

# Activar entorno virtual
.\venv\Scripts\Activate.ps1

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar servidor
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

Accede a: **http://localhost:8001**

---

## 📱 Desde el móvil (misma red)

### Paso 1: Encontrar tu IP
```powershell
ipconfig
```

Busca `IPv4 Address:` en la sección de tu conexión (ej: `192.168.1.100`)

### Paso 2: Acceder desde móvil
Escribe en el navegador del móvil:
```
http://192.168.1.100:8001
```

### Paso 3: Login
- Usuario: `admin`
- Contraseña: `tu_password_secreto`

---

## 🌐 Con ngrok (red pública)

```bash
# Terminal 1: Levanta la app (como se indicó arriba)

# Terminal 2: Inicia ngrok
ngrok http 8001
```

Copias la URL que aparece (ej: `https://abc123.ngrok.io`)

### Actualizar `.env`:
```env
ALLOWED_ORIGINS=https://abc123.ngrok.io,http://localhost:8001
```

### Reiniciar la app y acceder:
```
https://abc123.ngrok.io
```

---

## ❓ Solución de problemas

| Problema | Solución |
|----------|----------|
| "Login fallido" | Verifica credenciales en `.env` sean exactas |
| "No responde" | Asegúrate que Docker/uvicorn está levantado |
| "CORS bloqueado" | Agrega tu URL a `ALLOWED_ORIGINS` en `.env` |
| "Puerto 8001 en uso" | Cambia a otro puerto: `--port 8002` |

---

## 📚 Archivos importantes

- **`.env`** ← Crea este (credenciales + configuración)
- **`INSTRUCCIONES_SEGURIDAD.md`** ← Guía detallada
- **`SEGURIDAD.md`** ← Documentación técnica
- **`docker-compose.yml`** ← Para usar con Docker

---

**¡Listo! Tu app está segura y funcionando.** 🎉
