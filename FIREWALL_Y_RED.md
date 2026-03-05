# 🔒 CONFIGURACIÓN DE FIREWALL Y RED

## ¿Por qué no se conecta mi celular desde el PC?

A veces Windows Firewall bloquea la conexión. Aquí te muestro cómo solucionarlo.

---

## SOLUCIÓN 1: Abrir Puerto en Windows Firewall

### Opción A: Automática (Más fácil)

1. Abre **PowerShell como Administrador**
2. Copia y pega esto:

```powershell
# Permitir puerto 8001 en Firewall
netsh advfirewall firewall add rule name="FastAPI 8001" dir=in action=allow protocol=tcp localport=8001

# Verificar que se agregó la regla
netsh advfirewall firewall show rule name="FastAPI 8001"
```

3. Deberías ver:
```
Regla Name:         FastAPI 8001
Enabled:            Yes
Direction:          In(bound)
...
```

---

### Opción B: Manual (A través de GUI)

1. Abre **Defender de Windows** (o busca "Windows Defender")
2. Ve a **Firewall y protección de redes**
3. Haz clic en **"Permitir una aplicación a través del cortafuegos"**
4. Haz clic en **"Permitir otra aplicación"**
5. Busca `python.exe` o `uvicorn` en tu carpeta de Project
6. Haz clic en **"Agregar"**
7. Marca ambas: **Privada** y **Pública** (o solo Privada si es WiFi del hogar)
8. Haz clic en **"Aceptar"**

---

## SOLUCIÓN 2: Verificar que está en la misma Red

### En tu PC:
```powershell
ipconfig

# Busca la sección de tu conexión WiFi/Ethernet:
Dirección IPv4. . . . . . . . . : 192.168.1.100
Máscara de subred . . . . . . . : 255.255.255.0
Puerta de enlace principal . . . : 192.168.1.1
```

### En tu Celular:
```
Ajustes → Wi-Fi → SSID del WiFi
Verifica que dice: Connected (Conectado)
```

---

## SOLUCIÓN 3: Probar Conexión

### Desde tu PC:
```powershell
# Verifica que el servidor corre
netstat -ano | findstr :8001

# Deberías ver algo como:
# TCP    0.0.0.0:8001    0.0.0.0:0    LISTENING    12345
```

### Desde tu Celular:
1. Abre navegador
2. Ve a `http://192.168.1.100:8001` (reemplaza con tu IP)
3. Si ves la página → ¡Funciona! ✅
4. Si ves error → Revisa Firewall

---

## SOLUCIÓN 4: Desactivar Firewall (Temporal - NO RECOMENDADO)

⚠️ **Solo para pruebas locales**

```powershell
# Desactivar Firewall (Privada):
netsh advfirewall set privateprofile state off

# Reactivar Firewall (cuando termines):
netsh advfirewall set privateprofile state on
```

---

## 🧪 TEST de conectividad

### Test 1: Servidor corriendo

```powershell
# En tu PC, verifica:
netstat -ano | findstr :8001

# Deberías ver: LISTENING
```

### Test 2: IP accesible

```powershell
# Desde tu celular, abre navegador:
http://192.168.1.100:8001/

# Si ves página blanca con formulario → ✅ Funciona
```

### Test 3: Scanner funciona

```
1. Ve a http://192.168.1.100:8001/generar-qr
2. Genera un QR
3. Ve a http://192.168.1.100:8001
4. Escanea el QR con la cámara
5. Si detecta → ✅ Todo correcto
```

---

## 🚨 ERRORES COMUNES Y SOLUCIONES

| Error | Causa | Solución |
|-------|-------|----------|
| "No se puede acceder al sitio" | Firewall bloquea | Abre puerto 8001 en Firewall |
| "Se rechazó la conexión" | Servidor no corre | Ejecuta `docker-compose up` |
| "La dirección no es válida" | IP incorrecta | Usa `ipconfig` correcta |
| "Esperar..." (lento) | Red saturada | Reinicia router WiFi |
| "ERR_CONNECTION_RESET" | Firewall | Agrega excepción en Firewall |

---

## 📋 CHECKLIST FINAL

- [ ] Servidor corriendo en PC (`docker-compose up`)
- [ ] Firewall abre puerto 8001 (`netstat -ano | findstr :8001` muestra LISTENING)
- [ ] PC y celular en mismo WiFi
- [ ] IP correcta (`ipconfig` en PC)
- [ ] Acceso a `http://IP:8001` desde celular ✅
- [ ] Página de QR carga en celular (`http://IP:8001/generar-qr`)
- [ ] Generas código QR sin errores
- [ ] Descargas imagen del QR
- [ ] Pegas QR en vehículo
- [ ] Escaneas desde celular - Scanner detecta ✅
- [ ] Ubicación se guarda correctamente
- [ ] Dashboard muestra el mapa

---

## 🎓 INFORMACIÓN TÉCNICA

### Puerto usado:
- **8001** - FastAPI (tu app)

### Dentro de tu Red:
- PC: `192.168.X.X:8001`
- Celular: `192.168.X.X:8001` (mismo)

### Fuera de tu Red (Internet):
- No accesible por seguridad

---

## 🔐 SEGURIDAD EN PRODUCCIÓN

Si quieres usar esto en **internet público**:

1. ⚠️ **Usar HTTPS** (certificado SSL)
2. ⚠️ **Agregar autenticación**
3. ⚠️ **Validar inputs**
4. ⚠️ **Rate limiting**
5. ⚠️ **Usar IP estática**

(Esto va más allá del scope actual)

---

## 📞 CONTACTO RÁPIDO

Si aún no funciona:

1. Verifica `netstat -ano | findstr :8001` muestra LISTENING
2. Verifica misma red WiFi en ambos dispositivos
3. Desactiva VPN en celular
4. Reinicia router
5. Prueba a desactivar Firewall temporalmente

---

**¡Debería funcionar ahora! 🎉**
