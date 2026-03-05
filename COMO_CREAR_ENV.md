# 🔧 CREAR ESTE ARCHIVO: .env

**Ubicación:** `C:\codigoqr tatiana\.env`

**Copia y pega esto en un archivo de texto llamado `.env`:**

```
# ===== BASE DE DATOS =====
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432
DB_NAME=codigoqr_db

# ===== AUTENTICACIÓN =====
# Cambia estos valores a algo seguro en producción!

# Usuario para el login
ADMIN_USER=admin

# Contraseña para el login (CAMBIAR ANTES DE PRODUCCIÓN)
ADMIN_PASS=secret

# Secreto para firmar sesiones (mínimo 20 caracteres aleatorios)
SESSION_SECRET=mi_secreto_muy_largo_y_aleatorio_12345

# Dominios permitidos (CORS)
# Separa múltiples con comas
ALLOWED_ORIGINS=http://localhost:8001
```

---

## 📝 CÓMO CREAR EL ARCHIVO

### Opción A: VS Code (más fácil)
1. Abre VS Code
2. Click en Explorador (Ctrl+Shift+E)
3. Botón derecho en la carpeta raíz → "New File"
4. Nombre: `.env`
5. Pega el contenido de arriba
6. Ctrl+S para guardar

### Opción B: PowerShell
```powershell
# En C:\codigoqr tatiana
@"
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432
DB_NAME=codigoqr_db
ADMIN_USER=admin
ADMIN_PASS=secret
SESSION_SECRET=mi_secreto_muy_largo_y_aleatorio_12345
ALLOWED_ORIGINS=http://localhost:8001
"@ | Out-File -Encoding utf8 .env
```

### Opción C: Notepad
1. Abre Notepad
2. Pega el contenido de arriba
3. File → Save As
4. Nombre: `.env` (con punto adelante!)
5. Ubicación: `C:\codigoqr tatiana\`
6. Guardar

---

## ⚙️ PARÁMETROS EXPLICADOS

### Base de Datos
- `DB_USER`: Usuario de PostgreSQL (por defecto `postgres`)
- `DB_PASSWORD`: Contraseña BD (cambiar si usaste otra)
- `DB_HOST`: Donde está la BD
  - `db` si usas Docker
  - `localhost` si está en tu PC
- `DB_PORT`: Puerto PostgreSQL (5432 es estándar)
- `DB_NAME`: Nombre de la base de datos

### Autenticación
- `ADMIN_USER`: El nombre que usas para hacer login
- `ADMIN_PASS`: La contraseña para hacer login
  - **IMPORTANTE:** Cambiar en producción a algo fuerte
  - Ejemplo fuerte: `c0mpl3j0P@ssw0rd!xyz`
- `SESSION_SECRET`: Clave para firmar cookies/sesiones
  - Mínimo 20 caracteres aleatorios
  - Ejemplo: `aB3$xYzP9@mQ2!kLw5vN8rT`
  - Genera uno: https://www.random.org/strings/
- `ALLOWED_ORIGINS`: Qué URLs pueden acceder
  - `http://localhost:8001` = tu PC local
  - `http://192.168.1.100:8001` = desde móvil en red local
  - `https://abc123.ngrok.io` = con ngrok
  - Múltiples: `http://localhost:8001,http://192.168.1.100:8001`

---

## 🔐 SEGURIDAD: CAMBIOS RECOMENDADOS

### Para LOCAL (desarrollo):
```
ADMIN_USER=admin
ADMIN_PASS=dev123
SESSION_SECRET=dev_secret_for_local_testing_only
```

### Para PRODUCCIÓN:
```
ADMIN_USER=administrador_empresa
ADMIN_PASS=P@ssw0rdF0rte#2024!Xz9aB
SESSION_SECRET=aB3$xYzP9@mQ2!kLw5vN8rToLpM1!nJkH
ALLOWED_ORIGINS=https://miapp.com,https://www.miapp.com
```

---

## ✅ VERIFICAR QUE FUNCIONA

Después de crear `.env`:

```bash
# Levanta la app
docker-compose up
# O: uvicorn app.main:app --reload --host 127.0.0.1 --port 8001

# Accede a: http://localhost:8001
# Verás: Página de login
# Login: admin / secret (o lo que hayas puesto)
```

Si ves la página de login → `.env` está bien configurado ✅

---

## ⚠️ PROBLEMAS COMUNES

**"Could not load application..."**
- → Verifica que `.env` está en la carpeta correcta
- → Que no tiene extensión extra (`.env.txt` NO, `.env` SÍ)

**"Login fallido"**
- → Verifica credenciales exactas en `.env`
- → No dejes espacios: `ADMIN_PASS=secret` (no `ADMIN_PASS = secret`)

**"CORS error"**
- → Asegúrate de tener tu URL en `ALLOWED_ORIGINS`
- → Si accedes desde `http://192.168.1.100:8001`, agrégalo

---

## 💾 DESPUÉS DE CREAR `.env`

1. **NO lo publiques** en GitHub/repositorio público
2. **NO lo compartas** o makes commit
3. **SÍ tiene credenciales sensibles** - mantenlo privado
4. Si alguien lo ve, cambia `ADMIN_PASS` y `SESSION_SECRET` inmediatamente

---

**¡Listo! Tu `.env` está configurado.** 🎉
