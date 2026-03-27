# 📅 Guía: Reportes por Día

## ¿Qué es?

La nueva funcionalidad **"Reportes por Día"** te permite:
- **Seleccionar cualquier fecha** (usando un calendario)
- **Ver todos los escaneos** realizados ese día
- **Obtener información detallada** de cada escaneo:
  - Placa del vehículo
  - Nombre del vehículo
  - Hora exacta del escaneo
  - Responsable origen y destino
  - Ubicaciones (origen/destino)
  - Nivel de gasolina
  - Kilometraje
  - Observaciones

## 🚀 Cómo Acceder

### Opción 1: Desde el Menú Principal
1. Ve a la página de inicio: `http://localhost:8001/`
2. En la sección "Escanear Código QR" busca el enlace **"📅 Reportes por Día"**
3. Haz clic para abrir la página de reportes

### Opción 2: Acceso Directo
```
http://localhost:8001/reportes-diarios
```

### Opción 3: Desde tu Celular (con ngrok)
```
http://TU_URL_NGROK/reportes-diarios
```

## 📋 Cómo Usar

### Paso 1️⃣ - Seleccionar la Fecha
- Haz clic en el campo de fecha
- Selecciona el día que deseas consultar
- O haz clic en **"📍 Hoy"** para ver automáticamente el día actual

### Paso 2️⃣ - Consultar
- Haz clic en el botón **"🔍 Consultar"**
- Espera a que carguen los datos

### Paso 3️⃣ - Ver Resultados

La página mostrará dos secciones:

#### ✅ Vehículos Escaneados
Tabla con:
- **Placa**: Código QR del vehículo
- **Nombre**: Nombre del vehículo
- **Hora Escaneo**: Hora exacta
- **Responsable Origen**: Quién escaneó al salida
- **Responsable Destino**: Quién registró al llegada
- **Origen/Destino**: Ubicaciones
- **Gasolina**: Nivel de combustible registrado

#### ❌ Vehículos No Escaneados
Si algunos vehículos NO fueron escaneados, verás:
- **Placa**: Código QR
- **Nombre**: Nombre vehículo
- **Responsable Esperado**: Quién debería haber escaneado
- **Verificado Por**: Quién verificó que no se escaneó
- **Motivo**: Razón por la que no se escaneó
- **Hora Registro**: Cuándo se registró

### Paso 4️⃣ - Ver Resumen
En la parte superior ves las estadísticas:
- **Total Vehículos**: Cuántos están registrados
- **Escaneados**: Cuántos se escanearon ese día
- **No Escaneados**: Cuántos no se escanearon
- **Sin Registro**: Cuántos sin registro
- **Tasa Cumplimiento**: Porcentaje de cumplimiento

## 📥 Descargar a Excel

1. Una vez que consultes una fecha
2. En la parte inferior verás el botón **"⬇️ Descargar Excel"**
3. Haz clic para descargar un archivo Excel con todos los datos

### Contenido del Excel:
- Resumen con estadísticas
- Lista completa de vehículos escaneados
- Lista de vehículos no escaneados
- Información detallada por escaneo

## 💡 Ejemplos de Uso

### Ejemplo 1: Auditoría de un Día
```
1. Selecciona la fecha: 27/03/2026
2. Consulta
3. Revisa quiénes escanearon y quiénes no
4. Descarga el Excel para tu reporte
```

### Ejemplo 2: Verificar Cumplimiento
```
1. Selecciona hoy
2. Mira la "Tasa Cumplimiento %"
3. Si dice 80%, significa que el 80% de vehículos fueron escaneados
```

### Ejemplo 3: Investigar Incumplimientos
```
1. Mira la tabla "❌ No Escaneados"
2. Busca el vehículo y lee el "Motivo"
3. Contacta al responsable si es necesario
```

## ⚙️ Detalles Técnicos

### Ruta API
```
GET /api/escaneos-por-fecha?fecha=YYYY-MM-DD
```

### Respuesta Incluye:
```json
{
  "success": true,
  "fecha": "2026-03-27",
  "resumen": {
    "total_vehiculos": 50,
    "escaneados": 45,
    "no_escaneados": 3,
    "sin_registro": 2,
    "tasa_cumplimiento": 90.0
  },
  "escaneos": [...],
  "no_escaneados": [...]
}
```

## 🔒 Seguridad
- Solo usuarios autenticados pueden ver reportes
- Los datos mostrados son solo del día seleccionado
- No se registran accesos a los reportes

## ❓ Preguntas Frecuentes

### P: ¿Puedo ver reportes de hace 1 año?
**R:** Sí, siempre y cuando los datos estén en la base de datos.

### P: ¿Qué hago si no aparece un vehículo?
**R:** Significa que:
- No fue escaneado ese día y
- Tampoco fue registrado como "no escaneado"

### P: ¿El reporte en Excel se actualiza automáticamente?
**R:** No. Cada descarga te da un "snapshot" de ese momento.

### P: ¿Puedo filtrar solo escaneos de una persona?
**R:** No está disponible aún, pero puedes descargarlo a Excel y filtrar allí.

## 🐛 Solución de Problemas

### "Error al conectar con el servidor"
- Verifica que FastAPI esté corriendo (puerto 8001)
- Verifica que PostgreSQL esté activo

### "No hay datos"
- Verifica que los vehículos estén registrados
- Comprueba que haya escaneos registrados ese día

### Reportes no actualizan
- Recarga la página (F5)
- Consulta nuevamente

## 📞 Soporte
Para reportar bugs o sugerencias, contacta al equipo de desarrollo.
