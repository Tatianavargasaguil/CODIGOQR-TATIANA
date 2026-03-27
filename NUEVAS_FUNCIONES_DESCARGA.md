# 📥 NUEVAS CARACTERÍSTICAS - DESCARGAS Y BÚSQUEDAS

## ¿QUÉ SE AGREGÓ?

### 1️⃣ **Ver No Escaneados en Tiempo Real**

Nueva pestaña: **🔍 Ver No Escaneados**

**Permite buscar vehículos NO escaneados durante el día POR:**
- 👤 **Nombre del Responsable** (movilizador que debería haber escaneado)
- 🚗 **Placa/Código del vehículo**
- 📋 **Nombre del vehículo**

**Ejemplo:**
```
Supervisor quiere saber:
"¿Cuántos vehículos NO escaneó Juan Pérez hoy?"

→ Escribe: "Juan Pérez"
→ Presiona: Buscar
→ Ve tabla con todos sus incumplimientos
```

---

### 2️⃣ **Descargar Reportes en Excel**

**Dos opciones de descarga:**

#### **Option A: Reporte Completo**
```
Incluye:
├─ ✅ Vehículos que SÍ fueron escaneados
├─ ❌ Vehículos que NO fueron escaneados  
├─ ⚠️ Vehículos sin registro
└─ Todos con detalles: placa, hora, responsable, motivo
```

**Uso:**
1. Va a: 📊 **Reporte del Día**
2. Presiona: **📥 Descargar Excel**
3. Se descarga `reporte_diario_2024-01-15.xlsx`

#### **Opción B: Solo No Escaneados**
```
Incluye solo:
├─ Placa del vehículo
├─ Nombre del vehículo
├─ Responsable que debería haber escaneado
├─ Verificado por (persona en puerta)
├─ Motivo
└─ Hora del registro
```

**Uso:**
1. Va a: 🔍 **Ver No Escaneados**
2. Busca (ej: responsable, placa)
3. Presiona: **📥 Descargar Solo No Escaneados**
4. Se descarga `no_escaneados_2024-01-15.xlsx`

---

## 📊 FLUJO COMPLETO DEL DÍA

```
08:00 - 17:00 (Durante el día)
│
├─ Supervisor anota un vehículo que NO fue escaneado
│
├─ Persona en puerta escanea/busca el vehículo
│
├─ Sistema automáticamente detecta que NO fue escaneado
│
├─ Registra:
│  ├─ Quién debería haber escaneado (movilizador)
│  ├─ Quién lo registra (persona puerta)
│  ├─ Motivo
│  └─ Hora exacta
│
└─ TODO SE GUARDA EN BASE DE DATOS

16:00 - Supervisor revisa EN VIVO
│
├─ Va a: 🔍 Ver No Escaneados
│
├─ Filtra por responsable
│
├─ VE EXACTAMENTE QUIÉN INCUMPLIÓ
│
└─ ¡Puede tomar acciones INMEDIATAMENTE!

17:00 - Fin del día
│
├─ Descarga reporte en Excel
│
├─ Archiva para auditoría
│
└─ Tiene evidencia de todo
```

---

## 🎯 EJEMPLOS PRÁCTICOS

### **Caso 1: Supervisor desconfiado**

```
Supervisor: "No creo que Juan haya escaneado nada"

Va a: 🔍 Ver No Escaneados
Filtra: "Juan Pérez"
Resultado:
├─ NO escaneó Buseta 1
├─ NO escaneó Camión A
└─ NO escaneó Pickup B

Supervisor: "¡Probado! Juan incumplió 3 veces"
```

### **Caso 2: Una placa específica**

```
Supervisor: "¿Qué pasó con la Buseta 1?"

Va a: 🔍 Ver No Escaneados
Filtra: "Buseta 1"
Resultado:
├─ Placa: veh_bus_001
├─ Responsable: Juan Pérez
├─ Motivo: Se fue sin avisar
├─ Hora: 08:45 AM
└─ Verificado por: Carlos

Supervisor: "Ah, Juan la dejó sin escanear a las 8:45"
```

### **Caso 3: Auditoría al final del día**

```
17:30 - Supervisor
│
├─ Va a: 📊 Reporte del Día
│
├─ Presiona: 📥 Descargar Excel
│
├─ Obtiene archivo con:
│  ├─ Todos los vehículos del día
│  ├─ Cuál fue escaneado
│  ├─ Horas exactas
│  ├─ Responsables
│  └─ Motivos de faltas
│
└─ Lo guarda en carpeta: C:\Auditorías\2024-01-15\
```

---

## 🔄 API ENDPOINTS NUEVOS

### **Buscar No Escaneados con Filtros**
```bash
GET /api/search-unscanned?responsable=Juan&vehicle_code=veh_001&vehicle_name=Buseta
```

**Respuesta:**
```json
{
  "total": 2,
  "resultados": [
    {
      "vehicle_code": "veh_001",
      "vehicle_name": "Buseta 1",
      "responsable_esperado": "Juan Pérez",
      "motivo": "Se fue sin avisar",
      "registrado_a": "08:45:00",
      "verificado_por": "Carlos"
    }
  ]
}
```

---

### **Descargar Reporte Completo**
```bash
GET /api/export-daily-report-excel
```
Descarga: `reporte_diario_2024-01-15.xlsx`

---

### **Descargar Solo No Escaneados**
```bash
GET /api/export-unscanned-excel
```
Descarga: `no_escaneados_2024-01-15.xlsx`

---

## 💾 ARCHIVOS MODIFICADOS

- ✅ `app/main.py` → Agregados 3 nuevos endpoints
- ✅ `templates/puerta.html` → Nueva pestaña + funciones descarga

---

## ⚡ PRÓXIMOS PASOS

1. Accede a: `http://localhost:8001/puerta`
2. Prueba la nueva pestaña: 🔍 **Ver No Escaneados**
3. Filtra por responsable, placa, etc.
4. Descarga el Excel 📥

¡Listo! 🎉
