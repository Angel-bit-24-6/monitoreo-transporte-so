# Sistema de Detección de Eventos
## Monitoreo de Transporte y Seguridad Vial

**Versión:** 2.0

---

## 📋 Índice

1. [Visión General](#1-visión-general)
2. [Tipos de Eventos](#2-tipos-de-eventos)
3. [Detección Automática](#3-detección-automática)
4. [Configuración de Umbrales](#4-configuración-de-umbrales)
5. [Eventos en el Simulador](#5-eventos-en-el-simulador)
6. [Visualización en Dashboard](#6-visualización-en-dashboard)
7. [API de Eventos](#7-api-de-eventos)
8. [Consultas Útiles](#8-consultas-útiles)

---

## 1. Visión General

El sistema detecta **automáticamente** anomalías en el comportamiento de las unidades a través de una función PL/pgSQL que se ejecuta cada vez que se inserta una nueva posición GPS.

### Funcionamiento

```
┌──────────────┐
│ Dispositivo  │  Envía posición GPS
│ GPS          │  {lat, lon, speed, heading}
└──────┬───────┘
       │
       ▼
┌────────────────────────────────────────────┐
│ fn_insert_position_and_detect()            │
│                                            │
│ 1. INSERT INTO posicion                    │
│ 2. Buscar ruta asignada                    │
│ 3. Calcular distancia a ruta               │
│ 4. Verificar umbrales:                     │
│    - OUT_OF_BOUND (> 200m)                 │
│    - STOP_LONG (< 1.5 m/s por 120s)        │
│    - SPEEDING (> 22.22 m/s = 80 km/h)      │
│ 5. Si se detecta evento:                   │
│    INSERT INTO evento                      │
│ 6. RETURN (posicion_id, evento_id)         │
└────────────────────────────────────────────┘
       │
       ▼
┌──────────────┐
│ Backend      │  Broadcast a dashboards
│ WebSocket    │  → EVENT_ALERT
└──────────────┘
```

---

## 2. Tipos de Eventos

El sistema define **5 tipos de eventos** en la base de datos:

```sql
CREATE TYPE evento_tipo AS ENUM (
    'OUT_OF_BOUND',    -- Fuera de ruta
    'STOP_LONG',       -- Detención prolongada
    'SPEEDING',        -- Exceso de velocidad
    'GENERAL_ALERT',   -- Alerta general
    'INFO'             -- Información
);
```

### Estado de Implementación

| Tipo | Descripción | Detección Automática | Uso |
|------|-------------|----------------------|-----|
| `OUT_OF_BOUND` | Unidad fuera de ruta asignada | ✅ Sí | Desviaciones > 200m |
| `STOP_LONG` | Detención prolongada | ✅ Sí | Velocidad < 1.5 m/s por > 120s |
| `SPEEDING` | Exceso de velocidad | ✅ Sí | Velocidad > 22.22 m/s (80 km/h) |
| `GENERAL_ALERT` | Alerta general | ❌ No | Manual via API |
| `INFO` | Información | ❌ No | Manual via API |

---

## 3. Detección Automática

La función `fn_insert_position_and_detect()` implementa la lógica de detección.

**Ubicación:** `migrations/migrations_full_final_with_device_FIXED.sql:330`

### A) OUT_OF_BOUND (Fuera de Ruta)

#### Lógica

```sql
-- Buscar ruta asignada activa
SELECT ruta_id INTO v_ruta_id
FROM unidad_ruta_assignment
WHERE unidad_id = p_unidad_id
  AND (end_ts IS NULL OR end_ts > p_ts)
  AND start_ts <= p_ts
ORDER BY start_ts DESC
LIMIT 1;

-- Calcular distancia a la ruta
IF v_ruta_id IS NOT NULL THEN
    SELECT ST_Distance(
        ST_Transform(p_geom, 3857),
        ST_Transform(r.geom, 3857)
    ) INTO v_dist
    FROM ruta r
    WHERE r.id = v_ruta_id;

    -- Detectar evento si excede umbral
    IF v_dist > v_threshold_m THEN
        INSERT INTO evento (unidad_id, tipo, detalle, ts, posicion_id, metadata)
        VALUES (
            p_unidad_id,
            'OUT_OF_BOUND',
            'Distancia a ruta: ' || round(v_dist::numeric,2) || ' m',
            p_ts,
            v_pos_id,
            jsonb_build_object('ruta_id', v_ruta_id, 'distance_m', v_dist)
        )
        RETURNING id INTO v_event_id;
    END IF;
END IF;
```

#### Condiciones

1. **Ruta asignada**: La unidad debe tener una ruta asignada en `unidad_ruta_assignment`
2. **Distancia**: Punto GPS a línea de ruta > 200 metros (configurable)

#### Ejemplo

```
Unidad: UNIT-001
Posición GPS: (-1.6702, -78.6505)
Ruta asignada: Ruta A - Centro
Distancia calculada: 565.41 metros
Umbral: 200 metros
Resultado: ✅ Evento OUT_OF_BOUND creado (ID=42)

Metadata almacenada:
{
  "ruta_id": 1,
  "distance_m": 565.41
}
```

---

### B) STOP_LONG (Detención Prolongada)

#### Lógica

```sql
-- Verificar si la velocidad indica detención
IF COALESCE(p_speed,0) <= v_stop_speed_threshold THEN

    -- Si no estaba detenido, iniciar contador
    IF v_last_state.stop_start_ts IS NULL THEN
        UPDATE unidad_state
        SET stop_start_ts = p_ts,
            stop_lat = ST_Y(p_geom),
            stop_lon = ST_X(p_geom)
        WHERE unidad_id = p_unidad_id;

    -- Si ya estaba detenido, verificar si pasó el tiempo umbral
    ELSE
        v_stop_duration := EXTRACT(EPOCH FROM (p_ts - v_last_state.stop_start_ts));

        IF v_stop_duration >= v_stop_time_threshold THEN
            -- Solo crear evento si aún no se creó
            IF v_last_state.stop_event_created = FALSE THEN
                INSERT INTO evento (unidad_id, tipo, detalle, ts, posicion_id, metadata)
                VALUES (
                    p_unidad_id,
                    'STOP_LONG',
                    'Detención superior a ' || v_stop_time_threshold || ' s',
                    p_ts,
                    v_pos_id,
                    jsonb_build_object(
                        'stop_duration_s', v_stop_duration,
                        'stop_start_ts', v_last_state.stop_start_ts,
                        'stop_lat', v_last_state.stop_lat,
                        'stop_lon', v_last_state.stop_lon
                    )
                )
                RETURNING id INTO v_event_id;

                -- Marcar que ya se creó el evento
                UPDATE unidad_state
                SET stop_event_created = TRUE
                WHERE unidad_id = p_unidad_id;
            END IF;
        END IF;
    END IF;

-- Si se movió (velocidad > umbral), resetear contador
ELSE
    IF v_last_state.stop_start_ts IS NOT NULL THEN
        UPDATE unidad_state
        SET stop_start_ts = NULL,
            stop_lat = NULL,
            stop_lon = NULL,
            stop_event_created = FALSE
        WHERE unidad_id = p_unidad_id;
    END IF;
END IF;
```

#### Condiciones

1. **Velocidad baja**: ≤ 1.5 m/s (5.4 km/h)
2. **Duración**: ≥ 120 segundos (2 minutos)
3. **Una sola alerta**: Se crea el evento solo una vez por detención

#### Ejemplo - Timeline

```
T=0s    Velocidad = 0.5 m/s  → Inicia contador (stop_start_ts = T=0)
T=30s   Velocidad = 0.3 m/s  → Continúa detenido (30s acumulados)
T=60s   Velocidad = 0.7 m/s  → Continúa detenido (60s acumulados)
T=90s   Velocidad = 0.4 m/s  → Continúa detenido (90s acumulados)
T=120s  Velocidad = 0.6 m/s  → ✅ Evento STOP_LONG creado (ID=43)
T=150s  Velocidad = 0.5 m/s  → Continúa detenido (NO se crea evento de nuevo)
T=180s  Velocidad = 15.0 m/s → Reset del contador (stop_start_ts = NULL)
```

**Metadata almacenada:**
```json
{
  "stop_duration_s": 120.5,
  "stop_start_ts": "2025-10-14T10:30:00Z",
  "stop_lat": -1.6702,
  "stop_lon": -78.6505
}
```

---

### C) SPEEDING (Exceso de Velocidad)

#### Lógica

```sql
-- Obtener límite de velocidad de configuración
SELECT value::double precision INTO v_speed_limit
FROM sistema_config
WHERE key = 'SPEED_LIMIT_MS';

-- Detectar exceso de velocidad
IF p_speed IS NOT NULL
   AND v_speed_limit IS NOT NULL
   AND p_speed > v_speed_limit THEN

    INSERT INTO evento (unidad_id, tipo, detalle, ts, posicion_id, metadata)
    VALUES (
        p_unidad_id,
        'SPEEDING',
        'Velocidad: ' || round((p_speed * 3.6)::numeric, 2) || ' km/h (Límite: ' ||
        round((v_speed_limit * 3.6)::numeric, 2) || ' km/h)',
        p_ts,
        v_pos_id,
        jsonb_build_object(
            'speed_ms', p_speed,
            'speed_kmh', round((p_speed * 3.6)::numeric, 2),
            'limit_ms', v_speed_limit,
            'limit_kmh', round((v_speed_limit * 3.6)::numeric, 2)
        )
    )
    RETURNING id INTO v_event_id;
END IF;
```

#### Condiciones

1. **Velocidad reportada**: > 22.22 m/s (80 km/h por defecto)
2. **Límite configurable**: Se puede ajustar en `sistema_config`

#### Ejemplo

```
Unidad: UNIT-003
Velocidad reportada: 27.0 m/s (97.2 km/h)
Límite configurado: 22.22 m/s (80 km/h)
Resultado: ✅ Evento SPEEDING creado (ID=44)

Detalle: "Velocidad: 97.20 km/h (Límite: 80.00 km/h)"

Metadata almacenada:
{
  "speed_ms": 27.0,
  "speed_kmh": 97.20,
  "limit_ms": 22.22,
  "limit_kmh": 80.00
}
```

---

## 4. Configuración de Umbrales

Los umbrales se almacenan en la tabla `sistema_config` y también en `backend/.env` para el backend.

### Variables de Configuración

#### Backend (.env)

```env
# Archivo: backend/.env
OUT_OF_ROUTE_THRESHOLD_M=200
STOP_SPEED_THRESHOLD=1.5
STOP_TIME_THRESHOLD_S=120
```

#### Base de Datos

```sql
-- Tabla: sistema_config
INSERT INTO sistema_config (key, value, description) VALUES
('OUT_OF_ROUTE_THRESHOLD_M', '200', 'Metros de desviación para OUT_OF_BOUND'),
('STOP_SPEED_THRESHOLD', '1.5', 'Velocidad máxima (m/s) para considerar detenido'),
('STOP_TIME_THRESHOLD_S', '120', 'Segundos detenido para STOP_LONG'),
('SPEED_LIMIT_MS', '22.22', 'Límite de velocidad (m/s) = 80 km/h');
```

### Ajustar Umbrales

#### Cambiar en Base de Datos (recomendado para producción)

```sql
-- Cambiar umbral de distancia para OUT_OF_BOUND (300 metros)
UPDATE sistema_config
SET value = '300'
WHERE key = 'OUT_OF_ROUTE_THRESHOLD_M';

-- Cambiar umbral de tiempo para STOP_LONG (3 minutos)
UPDATE sistema_config
SET value = '180'
WHERE key = 'STOP_TIME_THRESHOLD_S';

-- Cambiar umbral de velocidad para detección de parada (2.0 m/s)
UPDATE sistema_config
SET value = '2.0'
WHERE key = 'STOP_SPEED_THRESHOLD';

-- Cambiar límite de velocidad para SPEEDING (100 km/h = 27.78 m/s)
UPDATE sistema_config
SET value = '27.78'
WHERE key = 'SPEED_LIMIT_MS';
```

#### Verificar Configuración

```sql
SELECT * FROM sistema_config ORDER BY key;
```

**Resultado esperado:**
```
              key              | value  |           description
-------------------------------+--------+----------------------------------
OUT_OF_ROUTE_THRESHOLD_M      | 200    | Metros de desviación para...
SPEED_LIMIT_MS                | 22.22  | Límite de velocidad...
STOP_SPEED_THRESHOLD          | 1.5    | Velocidad máxima...
STOP_TIME_THRESHOLD_S         | 120    | Segundos detenido para...
```

---

## 5. Eventos en el Simulador

El simulador GPS puede generar eventos realistas para pruebas.

**Archivo:** `simulator/gps_simulator_with_renewal.py`

### Eventos Simulados

| Evento | Comportamiento | Duración | Probabilidad |
|--------|---------------|----------|--------------|
| `out_of_route` | Desviación de ±0.005° (~500m) | 30-60s | 5% cada ciclo |
| `stop_long` | Velocidad 0-0.8 m/s | 60-180s | 5% cada ciclo |
| `speeding` | Velocidad 25-35 m/s (90-126 km/h) | 30-60s | 5% cada ciclo |

### Gestión de Eventos Prolongados

```python
class GPSDeviceSimulator:
    def __init__(self, ...):
        # Atributos para eventos prolongados
        self.current_event_type = None      # 'stop_long', 'out_of_route', 'speeding'
        self.event_start_time = None        # Timestamp de inicio
        self.event_duration = 0             # Duración en segundos

    async def _decide_event(self):
        """Decidir si iniciar un nuevo evento"""
        if self.current_event_type is not None:
            return  # Ya hay un evento activo

        import random
        if random.random() < 0.05:  # 5% de probabilidad
            event_type = random.choice(['stop_long', 'out_of_route', 'speeding'])
            duration = random.randint(60, 180)  # 60-180 segundos

            self.current_event_type = event_type
            self.event_start_time = time.time()
            self.event_duration = duration

            print(f"[{self.unidad_id}] ⚠️ INICIANDO evento: {event_type} por {duration}s")
```

### Salida del Simulador

```
[UNIT-001] Conectando a ws://localhost:8000/ws/device...
[UNIT-001] ✓ Autenticación exitosa
[UNIT-001] ⚠️ INICIANDO evento: stop_long por 125s
[UNIT-001] 🛑 Detenido (5s/125s) → ✓ ACK pos=458
[UNIT-001] 🛑 Detenido (10s/125s) → ✓ ACK pos=459
[UNIT-001] 🛑 Detenido (15s/125s) → ✓ ACK pos=460
...
[UNIT-001] 🛑 Detenido (120s/125s) → ✓ ACK pos=482 [EVENTO: ID=24 STOP_LONG]
[UNIT-001] 🛑 Detenido (125s/125s) → ✓ ACK pos=483
[UNIT-001] ✓ FINALIZANDO evento: stop_long
[UNIT-001] → Normal (15.2 m/s, 270°) → ✓ ACK pos=484
```

---

## 6. Visualización en Dashboard

El dashboard muestra eventos en tiempo real con íconos y colores distintivos.

**Archivos:** `frontend/index.html`, `frontend/src/main.js`

### Panel de Eventos

```javascript
// Mapeo de tipos a nombres legibles
const typeNames = {
    'OUT_OF_BOUND': '🚨 Fuera de Ruta',
    'STOP_LONG': '⏸️ Detención Prolongada',
    'SPEEDING': '⚡ Exceso de Velocidad',
    'GENERAL_ALERT': '⚠️ Alerta General',
    'INFO': 'ℹ️ Información'
};

// Renderizar evento
function renderEvent(event) {
    const eventDiv = document.createElement('div');
    eventDiv.className = `event-item ${event.tipo}`;
    eventDiv.innerHTML = `
        <div class="event-time">${formatTime(event.ts)}</div>
        <div class="event-unit">${event.unidad_id}</div>
        <div class="event-type">${typeNames[event.tipo]}</div>
        <div class="event-detail">${event.detalle}</div>
    `;
    return eventDiv;
}
```

### Estilos CSS

```css
.event-item {
    padding: 12px;
    margin-bottom: 10px;
    border-radius: 8px;
    background: white;
    border-left: 4px solid #ccc;
}

.event-item.OUT_OF_BOUND {
    border-left-color: #e74c3c;  /* Rojo */
    background: #ffebee;
}

.event-item.STOP_LONG {
    border-left-color: #f39c12;  /* Naranja */
    background: #fff3e0;
}

.event-item.SPEEDING {
    border-left-color: #e67e22;  /* Naranja oscuro */
    background: #ffe0cc;
}
```

### Ejemplo Visual

```
┌─────────────────────────────────────┐
│ 📋 Eventos Recientes                │
├─────────────────────────────────────┤
│ 20:33:39 - UNIT-001                 │
│ 🚨 Fuera de Ruta                    │
│ Distancia a ruta: 483.85 m          │
├─────────────────────────────────────┤
│ 20:28:53 - UNIT-002                 │
│ ⏸️ Detención Prolongada             │
│ Detención superior a 120 s          │
├─────────────────────────────────────┤
│ 20:25:17 - UNIT-003                 │
│ ⚡ Exceso de Velocidad               │
│ Velocidad: 97.20 km/h (Límite:80)   │
└─────────────────────────────────────┘
```

---

## 7. API de Eventos

### Endpoints Disponibles

#### GET /api/v1/eventos

Listar eventos con filtros.

**Parámetros de consulta:**
- `unidad_id` (opcional): Filtrar por unidad
- `tipo` (opcional): Filtrar por tipo de evento
- `start_date` (opcional): Fecha inicio (ISO 8601)
- `end_date` (opcional): Fecha fin (ISO 8601)
- `limit` (opcional): Número máximo de resultados (default: 50)
- `offset` (opcional): Offset para paginación (default: 0)

**Ejemplo:**
```bash
# Todos los eventos de UNIT-001
curl "http://localhost:8000/api/v1/eventos?unidad_id=UNIT-001"

# Solo eventos OUT_OF_BOUND de las últimas 24h
curl "http://localhost:8000/api/v1/eventos?tipo=OUT_OF_BOUND&start_date=2025-10-13T00:00:00Z"
```

**Respuesta:**
```json
[
  {
    "id": 42,
    "unidad_id": "UNIT-001",
    "tipo": "OUT_OF_BOUND",
    "detalle": "Distancia a ruta: 565.41 m",
    "ts": "2025-10-14T20:33:39Z",
    "posicion_id": 12345,
    "metadata": {
      "ruta_id": 1,
      "distance_m": 565.41
    },
    "created_at": "2025-10-14T20:33:40Z"
  }
]
```

#### GET /api/v1/eventos/{id}

Obtener detalles de un evento específico.

```bash
curl "http://localhost:8000/api/v1/eventos/42"
```

#### GET /api/v1/eventos/stats/summary

Obtener estadísticas de eventos.

```bash
curl "http://localhost:8000/api/v1/eventos/stats/summary"
```

**Respuesta:**
```json
{
  "total_eventos": 156,
  "por_tipo": {
    "OUT_OF_BOUND": 78,
    "STOP_LONG": 52,
    "SPEEDING": 26
  },
  "por_unidad": {
    "UNIT-001": 45,
    "UNIT-002": 38,
    "UNIT-003": 73
  },
  "ultimas_24h": 24
}
```

### Crear Eventos Manualmente

Para eventos `GENERAL_ALERT` e `INFO` que no se detectan automáticamente:

```bash
curl -X POST http://localhost:8000/api/v1/eventos \
  -H "Content-Type: application/json" \
  -d '{
    "unidad_id": "UNIT-001",
    "tipo": "GENERAL_ALERT",
    "detalle": "Mantenimiento programado - Próxima revisión",
    "ts": "2025-10-14T20:00:00Z",
    "metadata": {
      "tipo_mantenimiento": "preventivo",
      "proximo_servicio": "2025-10-21"
    }
  }'
```

---

## 8. Consultas Útiles

### Ver Eventos Recientes

```sql
SELECT
    id,
    unidad_id,
    tipo,
    detalle,
    ts,
    metadata
FROM evento
ORDER BY ts DESC
LIMIT 10;
```

### Estadísticas por Tipo de Evento (últimas 24h)

```sql
SELECT
    tipo,
    COUNT(*) as total,
    COUNT(DISTINCT unidad_id) as unidades_afectadas,
    MIN(ts) as primer_evento,
    MAX(ts) as ultimo_evento
FROM evento
WHERE ts >= now() - interval '24 hours'
GROUP BY tipo
ORDER BY total DESC;
```

**Resultado ejemplo:**
```
    tipo        | total | unidades_afectadas | primer_evento       | ultimo_evento
----------------+-------+--------------------+--------------------+--------------------
 OUT_OF_BOUND   |    45 |                  3 | 2025-10-14 00:15   | 2025-10-14 20:33
 STOP_LONG      |    28 |                  3 | 2025-10-14 01:22   | 2025-10-14 19:45
 SPEEDING       |    12 |                  2 | 2025-10-14 08:10   | 2025-10-14 18:20
```

### Unidades con Más Eventos

```sql
SELECT
    unidad_id,
    COUNT(*) as total_eventos,
    COUNT(*) FILTER (WHERE tipo = 'OUT_OF_BOUND') as fuera_ruta,
    COUNT(*) FILTER (WHERE tipo = 'STOP_LONG') as detenciones,
    COUNT(*) FILTER (WHERE tipo = 'SPEEDING') as excesos_velocidad,
    MAX(ts) as ultimo_evento
FROM evento
WHERE ts >= now() - interval '7 days'
GROUP BY unidad_id
ORDER BY total_eventos DESC;
```

### Eventos por Hora del Día

```sql
SELECT
    EXTRACT(HOUR FROM ts) as hora,
    COUNT(*) as total_eventos,
    COUNT(*) FILTER (WHERE tipo = 'OUT_OF_BOUND') as fuera_ruta,
    COUNT(*) FILTER (WHERE tipo = 'STOP_LONG') as detenciones
FROM evento
WHERE ts >= now() - interval '7 days'
GROUP BY hora
ORDER BY hora;
```

### Duración Promedio de Detenciones

```sql
SELECT
    unidad_id,
    COUNT(*) as total_detenciones,
    AVG((metadata->>'stop_duration_s')::numeric) as duracion_promedio_s,
    MAX((metadata->>'stop_duration_s')::numeric) as duracion_maxima_s
FROM evento
WHERE tipo = 'STOP_LONG'
  AND ts >= now() - interval '7 days'
GROUP BY unidad_id
ORDER BY duracion_promedio_s DESC;
```

---

## 📚 Referencias

### Archivos Relacionados

- **Base de Datos:** `migrations/migrations_full_final_with_device_FIXED.sql`
  - Función: `fn_insert_position_and_detect()` (línea 330)
  - Tabla: `evento` (línea 120)
  - Tabla: `sistema_config` (línea 180)

- **Backend:**
  - `backend/app/services/position_service.py` - Llama a la función PL/pgSQL
  - `backend/app/api/eventos.py` - Endpoints REST
  - `backend/app/websockets/device_handler.py` - Broadcast de eventos

- **Frontend:**
  - `frontend/src/main.js` - Visualización de eventos
  - `frontend/index.html` - Panel de eventos

- **Simulador:**
  - `simulator/gps_simulator_with_renewal.py` - Generación de eventos con renovación automática

### Documentación Adicional

- [ARQUITECTURA.md](ARQUITECTURA.md) - Diseño del sistema
- [TOKEN_SYSTEM.md](TOKEN_SYSTEM.md) - Sistema de autenticación
- [README.md](../README.md) - Documentación principal

---

**Versión:** 2.0
**Última actualización:** Octubre 2025
**Autor:** Sistema de Monitoreo UNACH
