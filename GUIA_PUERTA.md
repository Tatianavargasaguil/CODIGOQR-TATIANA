# 🚪 SISTEMA DE CONTROL DE PUERTA - VERIFICACIÓN DE ESCANEOS

## ¿QUÉ ES?

Sistema que permite a la **persona en la puerta** verificar si los vehículos fueron escaneados al salir, y si no, registrar que **NO fueron escaneados** junto con información del responsable que debería haberlo hecho.

---

## 🔄 FLUJO DE USO

### **Escenario: Un vehículo sale y la persona en puerta lo ve**

```
1️⃣ Movilizador sale sin escanear
   └─ Sistema NO tiene registro

2️⃣ Persona en puerta lo ve salir
   └─ Escanea el QR o busca manualmente

3️⃣ Sistema automáticamente detecta:
   ❌ "Este vehículo NO fue escaneado"

4️⃣ Persona en puerta registra:
   └─ Quién debería haber escaneado (movilizador)
   └─ Motivo (opcional)

5️⃣ Sistema genera REPORTE al final del día:
   └─ Vehículos que NO fueron escaneados
   └─ Quiénes fueron responsables
   └─ Tasa de cumplimiento
```

---

## 📱 CÓMO USAR

### **Acceso a la página de Puerta**

1. Entra a la aplicación con tu usuario/contraseña
2. Ve a: **http://localhost:8001/puerta**
3. Verás 3 opciones:
   - 📱 **Escanear Vehículo** (automático con cámara)
   - ✏️ **Búsqueda Manual** (escribir código/placa)
   - 📊 **Reporte del Día** (ver incumplimientos)

---

### **Opción 1: Escanear con QR**

```
1. La cámara se abre automáticamente
2. Apunta al código QR del vehículo
3. Sistema automáticamente te dice:
   ✅ "Vehículo escaneado a las 08:15"
   O
   ❌ "Vehículo NO fue escaneado"
```

Si NO fue escaneado:
```
4. Ingresa el nombre del movilizador
5. (Opcional) Escribe el motivo
6. Haz clic: "Confirmar como NO Escaneado"
7. Listo ✓
```

---

### **Opción 2: Búsqueda Manual**

```
1. Haz clic en la pestaña "Búsqueda Manual"
2. Escribe:
   - Código QR (ej: veh_abc123)
   - O nombre/placa (ej: Buseta 1)
3. Presiona "Buscar"
4. Mismo flujo que escaneo
```

---

### **Opción 3: Ver Reporte del Día**

```
1. Haz clic en "Reporte del Día"
2. Presiona "Cargar Reporte de Hoy"
3. Ves:
   ✅ Vehículos que SÍLLEVARON escaneados
   ❌ Vehículos que NO fueron escaneados
   📊 Tasa de cumplimiento (%)
```

---

## 🗄️ DATOS GUARDADOS

Cuando registras un vehículo como "NO escaneado", el sistema guarda:

| Campo | Valor | Ejemplo |
|-------|-------|---------|
| **Vehículo** | El código/nombre del veh | Buseta 1 |
| **Responsable Esperado** | Quién debería haberlo escaneado | Juan Pérez |
| **Verificado Por** | Quién registra la falta (persona puerta) | Carlos |
| **Motivo** | Por qué no fue escaneado | Se fue sin avisar |
| **Hora** | Cuándo se registró la falta | 08:30 AM |

---

## 📊 API - PARA DESARROLLADORES

### **1. Verificar si vehículo fue escaneado**

```bash
GET /api/check-vehicle-scan/{vehicle_code}
```

**Respuesta si SÍ fue escaneado:**
```json
{
  "was_scanned": true,
  "vehicle_name": "Buseta 1",
  "scanned_at": "08:15:30",
  "responsable": "Juan Pérez",
  "location": "Calle 5 con Carrera 10"
}
```

**Respuesta si NO fue escaneado:**
```json
{
  "was_scanned": false,
  "vehicle_name": "Buseta 1",
  "message": "Vehículo NO fue escaneado hoy"
}
```

---

### **2. Registrar vehículo como NO escaneado**

```bash
POST /api/mark-unscanned/{vehicle_code}

Body:
{
  "responsable_esperado": "Juan Pérez",
  "motivo": "Se fue sin avisar"
}
```

---

### **3. Obtener lista de NO escaneados HOY**

```bash
GET /api/unscanned-today
```

**Respuesta:**
```json
{
  "fecha": "2024-01-15",
  "total_vehiculos": 5,
  "escaneados_hoy": 3,
  "no_escaneados_hoy": 2,
  "tasa_cumplimiento": 60.0,
  "no_escaneados": [
    {
      "vehicle_name": "Buseta 1",
      "responsable_esperado": "Juan Pérez",
      "verificado_por": "Carlos",
      "motivo": "Se fue sin avisar",
      "registrado_a": "08:30:00"
    },
    {
      "vehicle_name": "Camión A",
      "responsable_esperado": "Pedro",
      "verificado_por": "Carlos",
      "motivo": null,
      "registrado_a": "09:15:00"
    }
  ]
}
```

---

### **4. Reporte completo del día**

```bash
GET /api/report-daily
```

**Respuesta:**
```json
{
  "fecha": "2024-01-15",
  "resumen": {
    "total_vehiculos": 5,
    "escaneados": 3,
    "no_escaneados": 2,
    "sin_registro": 0,
    "tasa_cumplimiento": 60.0
  },
  "escaneados": [...],
  "no_escaneados": [...]
}
```

---

## 🛠️ INSTALACIÓN

### **Paso 1: Ejecutar migración**

```bash
# En la carpeta del proyecto
python migrate_unscanned.py
```

Resultado esperado:
```
✅ Migración completada exitosamente
✓ Tabla 'unscanned_vehicles' creada
✓ Índices creados
```

### **Paso 2: Reiniciar servidor**

```bash
# Detén el servidor (Ctrl+C)
# Vuelve a iniciar
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

---

## 📋 CASOS DE USO

### **Caso 1: Movilizador incumplidor**
```
Supervisor nota que "Juan Pérez" SIEMPRE olvida escanear
→ Al final del día, revisa reporte
→ Ve que 3 vehículos asignados a Juan no fueron escaneados
→ Puede tomar acciones (multa, retención, etc.)
```

### **Caso 2: Proceso tardío**
```
Un vehículo sale a las 08:00 pero se olvida de escanear
→ A las 09:00 la aduana lo revisa
→ Persona en puerta se da cuenta: "No fue escaneado"
→ Registra el incidente
→ Se lo comunica al supervisor para investigar
```

### **Caso 3: Auditoria diaria**
```
Supervisor revisa reporte a las 15:00 (cada día)
→ Ve % de cumplimiento
→ Identifica patrones de incumplimiento
→ Toma medidas correctivas
```

---

## 🎯 RESUMEN

✅ **Antes (sin sistema):**
- Sistema basado en WhatsApp chismoso
- Confusión sobre quién escaneó o no
- Sin auditoría clara
- Imposible identificar patrones

✅ **Ahora (con sistema):**
- Registro automático en tiempo real
- Persona puerta verifica en segundos
- Auditoría completa y trazable
- Reporte claro de incumplimientos
- Identificación de responsables

---

## ❓ PREGUNTAS FRECUENTES

**P: ¿Qué pasa si escaneo un vehículo dos veces?**
R: Solo cuenta la primera vez que fue escaneado.

**P: ¿Puedo cambiar un registro de "no escaneado"?**
R: No, es un registro de auditoría. Pero puedes agregar notas adicionales.

**P: ¿El reporte se borra al siguiente día?**
R: No, los registros son permanentes. Puedes filtrar por fecha.

**P: ¿Qué pasa si olvido registrar un vehículo no escaneado?**
R: El reporte lo mostrará como "sin registro" (diferente a "no escaneado").

---

**Preguntas? Contacta al equipo de IT** 📞
