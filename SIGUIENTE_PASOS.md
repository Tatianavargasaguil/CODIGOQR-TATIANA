# 🎯 QUÉ HACER AHORA - GUÍA INMEDIATA

Tu aplicación ha sido **completamente asegurada**. Sigue estos pasos para usarla:

---

## 📍 PASO 1: Crear el archivo `.env` (5 min)

### Opción fácil: Copiar y pegar en VS Code

1. Abre VS Code
2. Click derecho en la carpeta raíz → "New File"
3. Nombre del archivo: `.env` (CON el punto adelante)
4. Pega esto:

```
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432
DB_NAME=codigoqr_db
ADMIN_USER=admin
ADMIN_PASS=secret123
SESSION_SECRET=mi_secreto_muy_largo_minimo_20_caracteres_random
ALLOWED_ORIGINS=http://localhost:8001
```

5. **Guardar** (Ctrl+S)

**✅ Listo!** El archivo está en la raíz: `C:\codigoqr tatiana\.env`

---

## 🚀 PASO 2: Ejecutar la aplicación

### Con Docker (Recomendado - más fácil)

```bash
# En PowerShell desde C:\codigoqr tatiana
docker-compose up
```

Espera 30 segundos. Luego:
- Abre navegador
- Vai a: **http://localhost:8001**
- Deberías ver una página de login

### Sin Docker (Python local)

```bash
# En PowerShell desde C:\codigoqr tatiana
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

Luego:
- Abre navegador
- Vai a: **http://localhost:8001**

---

## 🔐 PASO 3: Iniciar sesión

Cuando veas la página de login:
- **Usuario:** `admin` (o lo que pusiste en ADMIN_USER)
- **Contraseña:** `secret123` (o lo que pusiste en ADMIN_PASS)

Click en "Entrar" → **¡Acceso concedido!** ✅

---

## 📱 PASO 4: Acceder desde el móvil (opcional)

Si quieres escanear desde el móvil en la misma red:

1. En tu PC, abre PowerShell:
   ```bash
   ipconfig
   ```
   Busca `IPv4 Address:` (ejemplo: `192.168.1.100`)

2. En el navegador del móvil escribe:
   ```
   http://192.168.1.100:8001
   ```

3. Ingresa las credenciales (admin / secret123)

**¡Listo!** Ya puedes escanear desde el móvil.

---

## 📚 PARA ENTENDER MÁS DETALLES

Lee estos archivos **en este orden:**

1. **`INICIO_RAPIDO_SEGURO.md`** ← Start here (resumen visual)
2. **`INSTRUCCIONES_SEGURIDAD.md`** ← Guía completa
3. **`SEGURIDAD.md`** ← Documentación técnica (más avanzado)
4. **`COMO_CREAR_ENV.md`** ← Si necesitas ayuda con .env

---

## ⚠️ IMPORTANTE RECORDAR

✅ **DO:**
- Cambia `ADMIN_PASS` a algo fuerte si vas a producción
- Guarda `.env` seguro, no lo compartas
- Revisa `ALLOWED_ORIGINS` según tus dominios

❌ **DON'T:**
- Publiques `.env` en GitHub
- Dejes contraseña `secret123` en producción
- Expongas la app sin HTTPS en internet públicamente

---

## 🐛 SI ALGO FALLA

### Error: "Conexión rechazada"
```
→ Verifica que la app está levantada (terminal dice "Uvicorn running on...")
→ ¿Puerto 8001 está libre?
```

### Error: "Login fallido"
```
→ Verifica credenciales en .env sean exactas (mayúsculas/minúsculas importan)
→ ¿El archivo se guardó correctamente?
```

### Error: "CORS bloqueado"
```
→ ¿Tu URL está en ALLOWED_ORIGINS?
→ Si accedes desde ngrok: http://localhost:8001 ≠ https://abc123.ngrok.io
```

### Error: "SessionMiddleware not found"
```
→ Instala: pip install starlette
```

---

## 🎁 LO QUE CAMBIASTE

**Vulnerabilidades que SE ELIMINARON:**

❌ ~~Cualquiera podía acceder sin login~~
❌ ~~CORS abierto a todos~~
❌ ~~Variables de entorno hardcodeadas~~
❌ ~~Tu IP expuesta~~

**Protecciones que SE AGREGARON:**

✅ Login obligatorio
✅ CORS restringido
✅ Credenciales en `.env`
✅ Sesiones firmadas
✅ Endpoints protegidos

---

## 🚀 PRÓXIMO: Usar la app

Ahora que está segura, puedes:

1. **Generar código QR** (botón en la app)
2. **Escanear desde el móvil** (mismo código QR)
3. **Ver historial** de ubicaciones
4. **Todo está protegido** con tu login

---

##  TIPS

- Anota tus credenciales (ADMIN_USER y ADMIN_PASS) en un lugar seguro
- Si olvidas la contraseña, edita `.env` y cambiala
- Para producción, usa HTTPS obligatorio
- Con ngrok, asegúrate de agregar el dominio a `ALLOWED_ORIGINS`

---

**¿Dudas?** Lee los documentos de soporte incluidos.

**¿Listo?** ¡Abre terminal y ejecuta `docker-compose up`!

🎉 **¡Tu app está segura y funcionando!**
