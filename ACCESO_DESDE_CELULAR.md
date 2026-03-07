# 🚀 GUÍA: Acceder desde tu Celular

## Problem: "localhost:8001 no funciona en mi celular"

**Razón:** `localhost` es solo para la computadora local. Tu celular necesita la **IP de tu PC**.

---

## ✅ SOLUCIÓN: Usar la IP de tu Computadora

### 1️⃣ **Encontrar la IP de tu PC (Windows)**

#### Opción A: Línea de Comandos (Más rápido)
```powershell
ipconfig
```

Busca algo como:
```
Dirección IPv4. . . . . . . . . : 192.168.X.X
```

#### Opción B: Configuración Windows
1. Abre **Configuración**
2. Ve a **Red e Internet**
3. Haz clic en **Propiedades**
4. Busca "Dirección IPv4"

---

### 2️⃣ **Ejemplo Práctico**

Si tu PC tiene IP: `192.168.1.100`

- ❌ **NO USES:** `http://localhost:8001` (en celular)
- ✅ **USA:** `http://192.168.1.100:8001` (en celular)

---

### 3️⃣ **Acceder desde el Celular**

1. **Asegúrate que tu PC y celular estén en el MISMO WiFi**
2. **Abre el navegador en tu celular**
3. **Escribe:** `http://192.168.X.X:8001` (reemplaza con tu IP)
4. **Presiona Enter**

---

## 🔧 VERIFICAR que el Servidor está Corriendo

En tu PC, verifica que veas algo como:
```
Uvicorn running on http://0.0.0.0:8001
```

Si no lo ves, ejecuta:
```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

---

## 📋 CHECKLIST: Celular conectado

- ✅ PC y celular en el MISMO WiFi
- ✅ Servidor FastAPI corriendo en PC
- ✅ IP correcta (verifica con `ipconfig`)
- ✅ Puerto 8001 abierto (generalmente no hay problema)
- ✅ Prueba con: `http://IP:8001/generar-qr` primero

---

## 🎯 FLUJO COMPLETO

```
1. Genera código QR en PC o celular:
   → http://192.168.1.100:8001/generar-qr

2. Imprime o captura la imagen del QR

3. Pega el QR en tu vehículo

4. Escanea desde el celular:
   → http://192.168.1.100:8001

5. ¡Listo! El scanner funciona ahora
```

---

## ⚠️ PROBLEMAS COMUNES

### "No puedo acceder a la IP desde mi celular"

**Solución:**
1. Verifica que celular y PC estén en el MISMO WiFi
2. Desactiva VPN si la tienes (en celular)
3. En Windows, a veces el firewall bloquea:
   - Abre **Defensor de Windows**
   - Ve a **Firewall y protección de redes**
   - Haz clic en **Permitir que una aplicación acceda a través de Firewall**
   - Busca **Python** (o uvicorn) → Marca **Privada**

### "Debo reiniciar el servidor"

```powershell
# En tu PC (terminal)
docker-compose down
docker-compose up
```

O si es local:
```powershell
# Mata el proceso actual (Ctrl+C)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

---

## 🎥 VIDEO RESUMEN

**En tu PC:**
```
ipconfig → Anota tu IP (ej: 192.168.1.100)
```

**En tu Celular Browser:**
```
http://192.168.1.100:8001 → ¡A usar!
```

---

##  BONUS: Encontrar IP rápidamente

```powershell
# En PowerShell (una línea)
(Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceAlias -like "*WiFi*" -or $_.InterfaceAlias -like "*Ethernet*"}).IPAddress
```

O simplemente ejecuta:
```powershell
hostname -I
```

---

## 🎉 Listo!

Ahora puedes acceder desde cualquier dispositivo en tu red WiFi usando:

```
http://TU_IP_AQUI:8001
```

Ejemplo:
```
http://192.168.1.100:8001 ← Navega aquí
http://192.168.1.100:8001/generar-qr ← O aquí para crear QR
```

---

## 📱 PARA CREAR EL CÓDIGO QR DEL VEHÍCULO:

1. Accede a: `http://TU_IP:8001/generar-qr`
2. Haz clic en **"✨ Generar QR Automático"**
3. **Descarga o imprime** la imagen
4. **Pega en el vehículo**
5. **Escanea** desde `http://TU_IP:8001`

¡Listo para trackear tu vehículo! 🚗📍
