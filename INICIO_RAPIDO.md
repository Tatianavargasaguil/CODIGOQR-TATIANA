# ⚡ INICIO RÁPIDO - CODIGOQR TATIANA

## 🚀 En 5 Pasos Estás Listo

### Paso 1️⃣ - Inicia el servidor

En PowerShell en tu carpeta del proyecto:

```powershell
# Si es con Docker:
docker-compose up

# O si es local:
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

Deberías ver algo como:
```
✓ Application startup complete
Uvicorn running on http://0.0.0.0:8001
```

---

### Paso 2️⃣ - Abre en tu PC (localhost):

En el navegador de tu PC:
```
http://localhost:8001/generar-qr
```

---

### Paso 3️⃣ - Genera el Código QR del Vehículo

1. Haz clic en **"✨ Generar QR Automático"**
2. Se genera un código único (ej: `veh_a1b2c3d4`)
3. Haz clic en **"⬇️ Descargar Imagen"** (o captura screenshot)
4. **Imprime o pega la imagen en tu vehículo**

---

### Paso 4️⃣ - Accede desde tu Celular

En tu celular, abre un navegador y ve a:

```
http://TU_IP_AQUI:8001
```

**¿Dónde está mi IP?** → Lee [ACCESO_DESDE_CELULAR.md](ACCESO_DESDE_CELULAR.md)

---

### Paso 5️⃣ - Escanea y Registra

1. Apunta la cámara al código QR pegado en el vehículo
2. El scanner detecta automáticamente
3. Si es nuevo, llena el nombre del vehículo (placa, marca, etc)
4. Confirma ubicación
5. ¡Listo! Tu ubicación está guardada

---

## 📍 URLs Importantes

| URL | Descripción |
|-----|-------------|
| `http://localhost:8001` | Escanear QR (en tu PC) |
| `http://localhost:8001/generar-qr` | Crear códigos QR |
| `http://localhost:8001/dashboard/veh_a1b2c3d4` | Ver histórico de ubicaciones |

**En celular:** Reemplaza `localhost` con tu IP (ej: `192.168.1.100`)

---

## 🎯 Problemas Frecuentes

### "¿El scanner no funciona en mi celular?"

**Solución rápida:**
1. Ingresa el código manualmente (está en la interfaz)
2. Lee [ACCESO_DESDE_CELULAR.md](ACCESO_DESDE_CELULAR.md)
3. Verifica permisos de cámara en tu celular

### "¿Dónde veo las ubicaciones guardadas?"

Ve a:
```
http://YOUR_IP:8001/dashboard/veh_a1b2c3d4
```
(Reemplaza `veh_a1b2c3d4` con tu código QR)

### "¿Mi PE se reinicia?"

Ejecuta de nuevo el servidor:
```powershell
docker-compose down
docker-compose up
```

---

## 💾 Archivos Generados

Después de cada escaneo se guarda:
- 📌 **Ubicación GPS** (Latitud, Longitud)
- 🕒 **Fecha y Hora**
- 🚗 **Nombre del Vehículo**
- 📊 **Histórico en Base de Datos**

---

## 📋 Checklist Inicial

- [ ] Servidor iniciado en tu PC
- [ ] IP encontrada (ejemplo: 192.168.1.100)
- [ ] Código QR generado en `/generar-qr`
- [ ] QR pegado en el vehículo
- [ ] Acceso desde celular funciona
- [ ] Scanner detecta QR automáticamente
- [ ] Ubicación aparece en dashboard

---

## 📞 DATOS DE LA APP

**Tecnología Backend:**
- FastAPI (Python)
- PostgreSQL (Base de Datos)
- SQLAlchemy (ORM)

**Tecnología Frontend:**
- HTML5 QRCode (Scanner)
- Leaflet.js (Mapas)
- OpenStreetMap (Tiles)

**Características:**
- ✅ Escaneo QR en tiempo real
- ✅ Captura GPS automática
- ✅ Mapas interactivos
- ✅ Histórico de ubicaciones
- ✅ Responsivo para móvil

---

## 🎓 Próximos Pasos (Opcional)

- [ ] Agregar búsqueda por vehículo
- [ ] Exportar ubicaciones a CSV
- [ ] Alertas por zona (geofencing)
- [ ] Push notifications
- [ ] Múltiples usuarios

---

**¡Tu sistema está listo! 🎉**

Accede a `http://your-ip:8001` en tu celular y comienza a trackear.
