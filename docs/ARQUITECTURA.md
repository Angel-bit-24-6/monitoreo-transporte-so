# Arquitectura del Sistema
## Monitoreo de Transporte y Seguridad Vial

**Versión:** 2.0

---

## 📋 Índice

1. [Visión General](#1-visión-general)
2. [Arquitectura del Sistema](#2-arquitectura-del-sistema)
3. [Stack Tecnológico](#3-stack-tecnológico)
4. [Estructura de Carpetas](#4-estructura-de-carpetas)
5. [Flujos de Datos](#5-flujos-de-datos)
6. [Base de Datos](#6-base-de-datos)
7. [Componentes Backend](#7-componentes-backend)
8. [Componentes Frontend](#8-componentes-frontend)
9. [Protocolo WebSocket](#9-protocolo-websocket)
10. [Convenciones de Código](#10-convenciones-de-código)

---

## 1. Visión General

Sistema de monitoreo en tiempo real para transporte público que integra:
- **Rastreo GPS** de vehículos via WebSocket
- **Detección automática** de eventos (fuera de ruta, detenciones)
- **Dashboard web** con mapa interactivo (Leaflet.js)
- **Sistema de POIs** (22 lugares de interés precargados)
- **Chatbot inteligente** para búsqueda de lugares
- **API REST** completa para gestión

---

## 2. Arquitectura del Sistema

### Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                        CAPA DE CLIENTES                         │
├─────────────────┬───────────────────────┬───────────────────────┤
│                 │                       │                       │
│  Dispositivos   │   Dashboard Web       │   Aplicaciones       │
│  GPS            │   (Leaflet.js)        │   Externas           │
│  (WebSocket)    │   (WebSocket)         │   (REST API)         │
│                 │                       │                       │
└────────┬────────┴──────────┬────────────┴──────────┬───────────┘
         │                   │                       │
         ▼                   ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                     CAPA DE APLICACIÓN                          │
│                      Backend FastAPI                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │   API REST   │  │  WebSocket   │  │   Services   │        │
│  │              │  │              │  │              │        │
│  │ - Unidades   │  │ - Devices    │  │ - Auth       │        │
│  │ - Tokens     │  │ - Dashboard  │  │ - Position   │        │
│  │ - Rutas      │  │ - Chatbot    │  │ - POI        │        │
│  │ - Eventos    │  │              │  │              │        │
│  │ - POIs       │  │  Connection  │  │  Business    │        │
│  │ - Health     │  │  Manager     │  │  Logic       │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
│                                                                 │
│  ┌──────────────────────────────────────────────────┐         │
│  │           Core (Config + Database Pool)          │         │
│  └──────────────────────────────────────────────────┘         │
│                                                                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CAPA DE PERSISTENCIA                         │
│                 PostgreSQL 14 + PostGIS                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │   Tablas     │  │  Funciones   │  │   Índices    │        │
│  │              │  │   PL/pgSQL   │  │  Geoespaciales│       │
│  │ - unidad     │  │              │  │              │        │
│  │ - posicion   │  │ - insert_    │  │ - GiST       │        │
│  │ - evento     │  │   position_  │  │ - BTREE      │        │
│  │ - ruta       │  │   and_detect │  │ - Timestamp  │        │
│  │ - poi        │  │ - verify_    │  │              │        │
│  │ - token      │  │   token      │  │              │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Características Clave

**Comunicación:**
- ✅ **WebSocket bidireccional** - Dispositivos ↔ Backend ↔ Dashboards
- ✅ **REST API** - Operaciones CRUD, consultas, estadísticas
- ✅ **Async/Await** - Backend completamente asíncrono (FastAPI + asyncpg)

**Escalabilidad:**
- ✅ **Connection Pool** - asyncpg con 10-50 conexiones
- ✅ **Gestión de conexiones** - Connection Manager con locks
- ✅ **Suscripciones** - Dashboards solo reciben datos de unidades suscritas

**Confiabilidad:**
- ✅ **Reconexión automática** - WebSocket auto-reconnect
- ✅ **Heartbeat/Ping** - Mantener conexiones activas
- ✅ **Logging estructurado** - structlog con JSON output

---

## 3. Stack Tecnológico

### Backend

| Tecnología | Versión | Uso |
|------------|---------|-----|
| **Python** | 3.11+ | Lenguaje principal |
| **FastAPI** | 0.109.0 | Framework web async |
| **Uvicorn** | 0.27.0 | Servidor ASGI |
| **asyncpg** | 0.29.0 | Driver PostgreSQL async |
| **Pydantic** | 2.5.3 | Validación de datos |
| **structlog** | 24.1.0 | Logging estructurado |
| **websockets** | 12.0 | Comunicación bidireccional |
| **python-dotenv** | 1.0.0 | Gestión de variables de entorno |

### Frontend

| Tecnología | Versión | Uso |
|------------|---------|-----|
| **Vite** | 5.0.0 | Build tool moderno |
| **Leaflet.js** | 1.9.4 | Mapas interactivos |
| **JavaScript** | ES6+ | Vanilla JS (sin frameworks) |

### Base de Datos

| Tecnología | Versión | Uso |
|------------|---------|-----|
| **PostgreSQL** | 14+ | Base de datos relacional |
| **PostGIS** | 3.x | Extensión geoespacial |
| **pgcrypto** | - | Funciones de hashing (SHA-256) |

### DevOps

| Tecnología | Uso |
|------------|-----|
| **Docker** | Containerización |
| **Docker Compose** | Orquestación local |
| **Git** | Control de versiones |

---

## 4. Estructura de Carpetas

```
version_web/
│
├── 📚 DOCUMENTACIÓN
│   ├── README.md                       # Documentación principal
│   ├── QUICK_START.md                  # ⭐ Inicio rápido
│   ├── INSTALL_WINDOWS.md              # Instalación Windows
│   ├── INSTALL_UBUNTU.md               # Instalación Linux
│   ├── DEPLOYMENT.md                   # Guía de producción
│   │
│   └── docs/                           # Documentación técnica
│       ├── ARQUITECTURA.md             # Este archivo
│       ├── TOKEN_SYSTEM.md             # Sistema de tokens
│       └── EVENTOS.md                  # Sistema de eventos
│
├── 🔧 SCRIPTS DE INICIO
│   ├── start_backend.bat/.sh           # Inicia backend
│   ├── start_frontend.bat/.sh          # Inicia frontend
│   ├── start_simulator.bat/.sh         # Inicia simulador
│   └── setup.sh                        # Setup automático (Linux)
│
├── 🐳 DOCKER
│   ├── docker-compose.yml              # Orquestación
│   ├── backend/Dockerfile
│   └── frontend/Dockerfile
│
├── 🗄️ MIGRACIONES SQL
│   └── migrations/
│       └── migrations_full_final_with_device_FIXED.sql
│
├── 🐍 BACKEND (Python FastAPI)
│   └── backend/
│       ├── app/
│       │   ├── main.py                 # ⭐ App principal
│       │   │
│       │   ├── core/                   # Núcleo del sistema
│       │   │   ├── config.py           # Configuración (Pydantic Settings)
│       │   │   └── database.py         # Pool asyncpg
│       │   │
│       │   ├── models/                 # Modelos de datos
│       │   │   └── schemas.py          # Schemas Pydantic (validación)
│       │   │
│       │   ├── services/               # Lógica de negocio
│       │   │   ├── auth_service.py     # Autenticación y tokens
│       │   │   └── position_service.py # Procesamiento de posiciones
│       │   │
│       │   ├── websockets/             # Handlers WebSocket
│       │   │   ├── connection_manager.py  # Gestor global
│       │   │   ├── device_handler.py      # Dispositivos GPS
│       │   │   ├── dashboard_handler.py   # Dashboards web
│       │   │   └── chatbot_handler.py     # Chatbot inteligente
│       │   │
│       │   └── api/                    # Endpoints REST
│       │       ├── __init__.py         # Router principal
│       │       ├── unidades.py         # CRUD unidades
│       │       ├── tokens.py           # Gestión tokens
│       │       ├── rutas.py            # CRUD rutas
│       │       ├── eventos.py          # Consulta eventos
│       │       ├── pois.py             # CRUD POIs
│       │       └── health.py           # Health checks
│       │
│       ├── requirements.txt            # Dependencias
│       ├── .env.example                # Template configuración
│       ├── .env.testing                # Preset testing (10 min)
│       ├── .env.production             # Preset producción (30 días)
│       └── .env                        # ⚠️ Activo (NO en git)
│
├── 🌐 FRONTEND (Vite + Vanilla JS)
│   └── frontend/
│       ├── index.html                  # Página principal
│       ├── src/
│       │   └── main.js                 # ⭐ App JavaScript completa
│       ├── package.json                # Dependencias Node.js
│       └── vite.config.js              # Config Vite (proxy)
│
└── 🛰️ SIMULADOR GPS
    └── simulator/
        ├── gps_simulator_with_renewal.py  # ⭐ Simulador con renovación automática
        ├── device_config.json              # Configuración de dispositivos y tokens
        ├── routes_tapachula.json           # Rutas precargadas de Tapachula
        └── requirements.txt                # Dependencias Python
```

---

## 5. Flujos de Datos

### Flujo 1: Autenticación de Dispositivo

```
┌──────────────┐
│ Dispositivo  │
│ GPS          │
└──────┬───────┘
       │ 1. Conectar WebSocket
       │    ws://backend/ws/device
       ▼
┌──────────────────────────────┐
│ device_handler.py            │
│ handle() → accept()          │
└──────┬───────────────────────┘
       │ 2. Esperar AUTH
       ▼
┌──────────────────────────────┐
│ _authenticate()              │
│ - Recibe {token, device_id}  │
│ - Busca unidad_id por token  │
└──────┬───────────────────────┘
       │ 3. Verificar token
       ▼
┌──────────────────────────────┐
│ auth_service.py              │
│ verify_token()               │
└──────┬───────────────────────┘
       │ 4. Query PostgreSQL
       ▼
┌──────────────────────────────┐
│ fn_verify_unidad_token()     │
│ - Verifica hash SHA-256      │
│ - Verifica expires_at        │
│ - Verifica revoked           │
└──────┬───────────────────────┘
       │ 5. Resultado
       ▼
┌──────────────────────────────┐
│ device_handler.py            │
│ - Si válido: self.authenticated = True│
│ - Registrar en connection_manager    │
│ - Enviar AUTH_OK             │
│ - Iniciar _message_loop()    │
│                              │
│ - Si inválido: AUTH_FAILED   │
│ - Cerrar conexión            │
└──────────────────────────────┘
```

### Flujo 2: Inserción de Posición GPS

```
┌──────────────┐
│ Dispositivo  │
│ GPS          │
└──────┬───────┘
       │ 1. Enviar mensaje POS
       │    {type: "POS", lat, lon, speed, ...}
       ▼
┌────────────────────────────────────────────┐
│ device_handler.py                          │
│ _handle_position(data)                     │
│ - Valida PositionMessage con Pydantic      │
└──────┬─────────────────────────────────────┘
       │ 2. Procesar posición
       ▼
┌────────────────────────────────────────────┐
│ position_service.py                        │
│ insert_position_and_detect()               │
│ - unidad_id (de self.unidad_id autenticado)│
│ - lat, lon, speed, heading, ts, seq        │
└──────┬─────────────────────────────────────┘
       │ 3. Ejecutar función PL/pgSQL
       ▼
┌────────────────────────────────────────────┐
│ fn_insert_position_and_detect()            │
│                                            │
│ 1. INSERT INTO posicion                    │
│    → Devuelve posicion_id                  │
│                                            │
│ 2. Buscar ruta asignada                    │
│    SELECT * FROM unidad_ruta_assignment    │
│                                            │
│ 3. Calcular distancia a ruta               │
│    ST_Distance(point, ruta_geom)           │
│                                            │
│ 4. Detectar eventos:                       │
│    - OUT_OF_BOUND (> 200m)                 │
│    - STOP_LONG (speed < 1.5 m/s por 120s)│
│    - SPEEDING (speed > límite)             │
│                                            │
│ 5. Si evento: INSERT INTO evento           │
│    → Devuelve evento_id                    │
│                                            │
│ 6. RETURN (posicion_id, evento_id)         │
└──────┬─────────────────────────────────────┘
       │ 4. Resultado
       ▼
┌────────────────────────────────────────────┐
│ device_handler.py                          │
│ - Enviar ACK al dispositivo                │
│   {type: "ACK", posicion_id, event_id}     │
│                                            │
│ - Broadcast a dashboards:                  │
│   → _broadcast_position_update()           │
│   → _broadcast_event_alert() (si evento)   │
└────────────────────────────────────────────┘
```

### Flujo 3: Dashboard en Tiempo Real

```
┌──────────────┐
│ Dashboard    │
│ Web          │
└──────┬───────┘
       │ 1. Conectar WebSocket
       │    ws://backend/ws/dashboard
       ▼
┌────────────────────────────────────────────┐
│ dashboard_handler.py                       │
│ handle() → accept()                        │
│ - NO requiere autenticación (dashboard)    │
└──────┬─────────────────────────────────────┘
       │ 2. Enviar SUBSCRIBE
       │    {type: "SUBSCRIBE", unidad_ids: ["UNIT-001", "UNIT-002"]}
       ▼
┌────────────────────────────────────────────┐
│ _handle_subscribe()                        │
│ - Registrar en connection_manager          │
│ - self.subscribed_unidades = ["UNIT-001", "UNIT-002"]│
└────────────────────────────────────────────┘
       │
       │ 3. Cuando dispositivo envía posición
       ▼
┌────────────────────────────────────────────┐
│ device_handler.py                          │
│ _broadcast_position_update()               │
└──────┬─────────────────────────────────────┘
       │
       ▼
┌────────────────────────────────────────────┐
│ connection_manager.py                      │
│ broadcast_to_unidad_subscribers()          │
│ - Para cada dashboard con "UNIT-001" suscrito│
│ - Enviar POSITION_UPDATE                   │
│   {type: "POSITION_UPDATE", unidad_id,     │
│    posicion_id, lat, lon, speed, ...}      │
└──────┬─────────────────────────────────────┘
       │
       ▼
┌────────────────────────────────────────────┐
│ Dashboard Web (main.js)                    │
│ handleWebSocketMessage()                   │
│ - Actualizar marcador en mapa Leaflet     │
│ - Actualizar panel de información          │
│ - Si evento: mostrar alerta                │
└────────────────────────────────────────────┘
```

---

## 6. Base de Datos

### Tablas Principales

#### `unidad`
```sql
CREATE TABLE unidad (
    id TEXT PRIMARY KEY,           -- "UNIT-001"
    placa TEXT NOT NULL,           -- "ABC-123"
    chofer TEXT,                   -- "Juan Pérez"
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

#### `posicion`
```sql
CREATE TABLE posicion (
    id BIGSERIAL PRIMARY KEY,
    unidad_id TEXT NOT NULL REFERENCES unidad(id),
    ts TIMESTAMPTZ NOT NULL,               -- Timestamp del GPS
    geom GEOMETRY(Point, 4326) NOT NULL,   -- PostGIS Point
    speed DOUBLE PRECISION,                -- m/s
    heading INTEGER,                       -- 0-359 grados
    seq BIGINT,                            -- Secuencia del dispositivo
    raw_payload JSONB,                     -- Mensaje original
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Índices geoespaciales
CREATE INDEX idx_posicion_geom ON posicion USING GIST(geom);
CREATE INDEX idx_posicion_unidad_ts ON posicion(unidad_id, ts DESC);
```

#### `evento`
```sql
CREATE TYPE evento_tipo AS ENUM (
    'OUT_OF_BOUND',    -- Fuera de ruta
    'STOP_LONG',       -- Detención prolongada
    'SPEEDING',        -- Exceso de velocidad
    'GENERAL_ALERT',   -- Alerta general
    'INFO'             -- Información
);

CREATE TABLE evento (
    id BIGSERIAL PRIMARY KEY,
    unidad_id TEXT NOT NULL REFERENCES unidad(id),
    tipo evento_tipo NOT NULL,
    detalle TEXT,
    ts TIMESTAMPTZ NOT NULL,
    posicion_id BIGINT REFERENCES posicion(id),
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_evento_unidad_ts ON evento(unidad_id, ts DESC);
CREATE INDEX idx_evento_tipo ON evento(tipo);
```

#### `ruta`
```sql
CREATE TABLE ruta (
    id SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL,
    descripcion TEXT,
    geom GEOMETRY(LineString, 4326) NOT NULL,  -- PostGIS LineString
    activa BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_ruta_geom ON ruta USING GIST(geom);
```

#### `unidad_token`
```sql
CREATE TABLE unidad_token (
    id SERIAL PRIMARY KEY,
    unidad_id TEXT NOT NULL REFERENCES unidad(id),
    device_id TEXT NOT NULL,               -- "GPS-001"
    token_hash BYTEA NOT NULL,             -- SHA-256 (32 bytes)
    expires_at TIMESTAMPTZ,                -- NULL = sin expiración
    created_at TIMESTAMPTZ DEFAULT now(),
    last_used TIMESTAMPTZ,
    revoked BOOLEAN DEFAULT FALSE,

    UNIQUE(unidad_id, device_id, token_hash)
);

CREATE INDEX idx_token_hash ON unidad_token(token_hash);
CREATE INDEX idx_token_device ON unidad_token(unidad_id, device_id);
```

#### `poi` (Puntos de Interés)
```sql
CREATE TYPE poi_categoria AS ENUM (
    'hospital',
    'farmacia',
    'papeleria',
    'gasolinera',
    'banco'
);

CREATE TABLE poi (
    id SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL,
    categoria poi_categoria NOT NULL,
    direccion TEXT,
    telefono TEXT,
    horario TEXT,
    geom GEOMETRY(Point, 4326) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_poi_geom ON poi USING GIST(geom);
CREATE INDEX idx_poi_categoria ON poi(categoria);
```

### Funciones PL/pgSQL Clave

#### `fn_insert_position_and_detect()`

Función principal que:
1. Inserta nueva posición
2. Calcula distancia a ruta asignada
3. Detecta eventos automáticamente
4. Retorna (posicion_id, evento_id)

**Ubicación:** `migrations_full_final_with_device_FIXED.sql:330`

#### `fn_verify_unidad_token()`

Verifica validez de un token:
- Hash coincide
- No está revocado
- No ha expirado

**Ubicación:** `migrations_full_final_with_device_FIXED.sql:279`

#### `fn_create_unidad_token_for_device()`

Crea nuevo token para un dispositivo:
- Genera token aleatorio (32 bytes)
- Calcula hash SHA-256
- Opcionalmente revoca tokens antiguos
- Retorna (token_plain, token_id)

**Ubicación:** `migrations_full_final_with_device_FIXED.sql:219`

---

## 7. Componentes Backend

### Core: Configuración

**Archivo:** `backend/app/core/config.py`

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    DB_MIN_POOL_SIZE: int = 10
    DB_MAX_POOL_SIZE: int = 50

    # Token Configuration
    TOKEN_TTL_SECONDS: int = 600
    TOKEN_RENEWAL_THRESHOLD_MINUTES: int = 7
    TOKEN_RENEWAL_CHECK_INTERVAL_SECONDS: int = 60
    TOKEN_GRACE_PERIOD_DAYS: int = 7

    # System Config
    OUT_OF_ROUTE_THRESHOLD_M: float = 200.0
    STOP_SPEED_THRESHOLD: float = 1.5
    STOP_TIME_THRESHOLD_S: int = 120

    class Config:
        env_file = ".env"

settings = Settings()
```

**Características:**
- Carga automática desde `.env`
- Validación con Pydantic
- Valores por defecto
- Type hints

### Core: Database Pool

**Archivo:** `backend/app/core/database.py`

```python
import asyncpg

class Database:
    def __init__(self):
        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        self._pool = await asyncpg.create_pool(
            settings.DATABASE_URL,
            min_size=settings.DB_MIN_POOL_SIZE,
            max_size=settings.DB_MAX_POOL_SIZE
        )

    async def fetch_one(self, query: str, *args):
        async with self._pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetch_all(self, query: str, *args):
        async with self._pool.acquire() as conn:
            return await conn.fetch(query, *args)

db = Database()
```

**Características:**
- Connection pooling
- Async/await
- Context managers
- Singleton pattern

### Services: Lógica de Negocio

#### `auth_service.py`

Responsabilidades:
- Verificar tokens
- Crear nuevos tokens
- Revocar tokens
- Verificar necesidad de renovación

Métodos clave:
- `verify_token(unidad_id, token_plain) -> bool`
- `create_token(unidad_id, device_id, ttl_seconds, revoke_old) -> tuple`
- `should_renew_token(unidad_id, device_id, renewal_threshold_minutes) -> bool`

#### `position_service.py`

Responsabilidades:
- Insertar posiciones
- Detectar eventos
- Consultar historial

Métodos clave:
- `insert_position_and_detect(...) -> tuple[int, Optional[int]]`
- `get_event_details(evento_id) -> dict`

### WebSocket: Connection Manager

**Archivo:** `backend/app/websockets/connection_manager.py`

```python
class WebSocketConnection:
    websocket: WebSocket
    client_type: ClientType  # DEVICE | DASHBOARD
    client_id: str
    unidad_id: Optional[str]

class ConnectionManager:
    def __init__(self):
        self.device_connections: Dict[str, WebSocketConnection] = {}
        self.dashboard_connections: Dict[str, WebSocketConnection] = {}
        self.subscriptions: Dict[str, Set[str]] = {}  # unidad_id → set(dashboard_ids)
        self._lock = asyncio.Lock()

    async def broadcast_to_unidad_subscribers(self, unidad_id: str, message: dict):
        """Enviar mensaje a todos los dashboards suscritos a una unidad"""
        subscriber_ids = self.subscriptions.get(unidad_id, set())
        for dashboard_id in subscriber_ids:
            if dashboard_id in self.dashboard_connections:
                conn = self.dashboard_connections[dashboard_id]
                await conn.websocket.send_json(message)

connection_manager = ConnectionManager()
```

### WebSocket: Device Handler

**Archivo:** `backend/app/websockets/device_handler.py`

Métodos principales:
- `handle()` - Punto de entrada
- `_authenticate()` - Verificar token
- `_message_loop()` - Procesar mensajes
- `_handle_position()` - Insertar posición
- `_token_renewal_checker()` - Verificación periódica (cada 60s/3600s)
- `_send_token_renewal()` - Enviar nuevo token

### API REST: Estructura

**Archivo:** `backend/app/api/__init__.py`

```python
from fastapi import APIRouter
from .unidades import router as unidades_router
from .tokens import router as tokens_router
from .rutas import router as rutas_router
from .eventos import router as eventos_router
from .pois import router as pois_router
from .health import router as health_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(unidades_router)
api_router.include_router(tokens_router)
api_router.include_router(rutas_router)
api_router.include_router(eventos_router)
api_router.include_router(pois_router)
api_router.include_router(health_router)
```

**Convención:**
- Cada recurso en su propio archivo
- Router con prefix y tags
- Importación centralizada en `__init__.py`
- Auto-registro en FastAPI

---

## 8. Componentes Frontend

### Estructura del Frontend

**Archivo único:** `frontend/src/main.js` (~1500 líneas)

### Estado Global

```javascript
const state = {
    map: null,
    ws: null,
    chatbotWs: null,
    markers: {},              // unidad_id → L.marker
    subscribedUnits: new Set(),
    pois: [],
    poiMarkers: [],
    highlightedPois: new Set()
};
```

### Módulos Principales

#### 1. Inicialización del Mapa

```javascript
async function initMap() {
    state.map = L.map('map').setView([14.9067, -92.2631], 13);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap'
    }).addTo(state.map);

    await loadPOIs();
    await loadUnits();
    initWebSocket();
    initChatbot();
}
```

#### 2. WebSocket para Posiciones

```javascript
function initWebSocket() {
    state.ws = new WebSocket('ws://localhost:8000/ws/dashboard');

    state.ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        handleWebSocketMessage(message);
    };

    state.ws.onopen = () => {
        // Suscribirse a todas las unidades
        state.ws.send(JSON.stringify({
            type: 'SUBSCRIBE',
            unidad_ids: Array.from(state.subscribedUnits)
        }));
    };
}

function handleWebSocketMessage(message) {
    switch(message.type) {
        case 'POSITION_UPDATE':
            updateMarkerPosition(message);
            break;
        case 'EVENT_ALERT':
            showEventAlert(message);
            break;
        case 'CONNECTION_STATE':
            updateConnectionState(message);
            break;
    }
}
```

#### 3. Chatbot WebSocket

```javascript
function initChatbot() {
    state.chatbotWs = new WebSocket('ws://localhost:8000/ws/chatbot');

    state.chatbotWs.onmessage = (event) => {
        const message = JSON.parse(event.data);

        if (message.type === 'BOT_MESSAGE') {
            displayBotMessage(message.message);

            // Resaltar POIs en mapa si hay datos
            if (message.data?.action === 'highlight_pois') {
                highlightPOIsOnMap(message.data.pois, message.data.zoom_to_fit);
            }
        }
    };
}
```

#### 4. Gestión de Marcadores

```javascript
function updateMarkerPosition(data) {
    const { unidad_id, lat, lon, speed, heading } = data;

    if (!state.markers[unidad_id]) {
        // Crear nuevo marcador
        const marker = L.marker([lat, lon], {
            icon: createCustomIcon(unidad_id),
            rotationAngle: heading
        }).addTo(state.map);

        marker.bindPopup(createPopupContent(data));
        state.markers[unidad_id] = marker;
    } else {
        // Actualizar posición existente
        const marker = state.markers[unidad_id];
        marker.setLatLng([lat, lon]);
        marker.setRotationAngle(heading);
        marker.getPopup().setContent(createPopupContent(data));
    }
}
```

#### 5. Sistema de POIs

```javascript
async function loadPOIs() {
    const response = await fetch('http://localhost:8000/api/v1/pois');
    state.pois = await response.json();

    state.pois.forEach(poi => {
        const icon = getPOIIcon(poi.categoria);
        const marker = L.marker([poi.lat, poi.lon], { icon })
            .bindPopup(createPOIPopup(poi))
            .addTo(state.map);

        state.poiMarkers.push(marker);
    });
}

function highlightPOIsOnMap(pois, zoomToFit) {
    // Limpiar resaltados anteriores
    clearHighlightedPOIs();

    // Resaltar POIs encontrados
    pois.forEach(poi => {
        const marker = state.poiMarkers.find(m => m.options.poiId === poi.id);
        if (marker) {
            marker.setIcon(getHighlightedIcon(poi.categoria));
            state.highlightedPois.add(poi.id);
        }
    });

    // Ajustar zoom para mostrar todos
    if (zoomToFit && pois.length > 0) {
        const bounds = L.latLngBounds(pois.map(p => [p.lat, p.lon]));
        state.map.fitBounds(bounds, { padding: [50, 50] });
    }
}
```

---

## 9. Protocolo WebSocket

### Mensajes: Dispositivo → Backend

#### AUTH
```json
{
  "type": "AUTH",
  "token": "abc123def456...",
  "device_id": "GPS-001"
}
```

#### POS
```json
{
  "type": "POS",
  "lat": -1.6702,
  "lon": -78.6505,
  "speed": 15.5,
  "heading": 270,
  "timestamp": "2025-10-14T10:30:00Z",
  "seq": 123
}
```

#### PING
```json
{
  "type": "PING"
}
```

#### TOKEN_RENEWAL_ACK
```json
{
  "type": "TOKEN_RENEWAL_ACK",
  "new_token_saved": true,
  "message": "Token guardado exitosamente"
}
```

### Mensajes: Backend → Dispositivo

#### AUTH_OK
```json
{
  "type": "AUTH_OK",
  "unidad_id": "UNIT-001",
  "message": "Autenticación exitosa"
}
```

#### AUTH_FAILED
```json
{
  "type": "AUTH_FAILED",
  "message": "Autenticación fallida",
  "reason": "Token inválido o expirado"
}
```

#### ACK
```json
{
  "type": "ACK",
  "posicion_id": 45678,
  "event_id": 123,
  "timestamp": "2025-10-14T10:30:01Z"
}
```

#### TOKEN_RENEWAL
```json
{
  "type": "TOKEN_RENEWAL",
  "new_token": "xyz789abc456...",
  "expires_at": "2025-11-13T10:30:00Z",
  "grace_period_days": 7,
  "message": "Token renovado. Actualice su configuración."
}
```

#### PONG
```json
{
  "type": "PONG",
  "timestamp": "2025-10-14T10:30:00Z"
}
```

### Mensajes: Dashboard ↔ Backend

#### SUBSCRIBE (D → B)
```json
{
  "type": "SUBSCRIBE",
  "unidad_ids": ["UNIT-001", "UNIT-002"]
}
```

#### UNSUBSCRIBE (D → B)
```json
{
  "type": "UNSUBSCRIBE",
  "unidad_ids": ["UNIT-002"]
}
```

#### POSITION_UPDATE (B → D)
```json
{
  "type": "POSITION_UPDATE",
  "unidad_id": "UNIT-001",
  "posicion_id": 45678,
  "lat": -1.6702,
  "lon": -78.6505,
  "speed": 15.5,
  "heading": 270,
  "timestamp": "2025-10-14T10:30:00Z"
}
```

#### EVENT_ALERT (B → D)
```json
{
  "type": "EVENT_ALERT",
  "unidad_id": "UNIT-001",
  "event_id": 123,
  "event_tipo": "OUT_OF_BOUND",
  "detalle": "Distancia a ruta: 350.5 m",
  "timestamp": "2025-10-14T10:30:00Z",
  "posicion_id": 45678
}
```

#### CONNECTION_STATE (B → D)
```json
{
  "type": "CONNECTION_STATE",
  "unidad_id": "UNIT-001",
  "is_connected": true
}
```

---

## 10. Convenciones de Código

### Nombres de Archivos

- **Python:** `snake_case.py`
- **JavaScript:** `camelCase.js` (pero usamos `main.js` por simplicidad)
- **Batch:** `start_something.bat`
- **Shell:** `start_something.sh`
- **Config:** `.env`, `docker-compose.yml`
- **Docs:** `UPPERCASE.md`

### Estructura Python

```python
# 1. Imports
from fastapi import APIRouter
from typing import Optional

# 2. Logger
logger = structlog.get_logger()

# 3. Router/Class
router = APIRouter(prefix="/recurso", tags=["Recurso"])

# 4. Endpoints/Methods
@router.get("")
async def list_items():
    """Docstring con descripción"""
    pass
```

### Estructura JavaScript

```javascript
// 1. Estado global
const state = { ... };

// 2. Funciones auxiliares
function helperFunction() { }

// 3. Event handlers
async function handleSomething() { }

// 4. Inicialización
async function init() { }
init();
```

### Logging Estructurado

```python
# Backend
logger.info(
    "event_name",
    key1="value1",
    key2=value2,
    exc_info=True  # si hay excepción
)
```

Genera:
```json
{
  "event": "event_name",
  "key1": "value1",
  "key2": "value2",
  "timestamp": "2025-10-14T10:30:00Z",
  "level": "info"
}
```

---

## 📚 Referencias

### Documentación Relacionada

- [README.md](../README.md) - Documentación principal
- [TOKEN_SYSTEM.md](TOKEN_SYSTEM.md) - Sistema completo de tokens
- [EVENTOS.md](EVENTOS.md) - Sistema de detección de eventos
- [QUICK_START.md](../QUICK_START.md) - Inicio rápido

### Recursos Externos

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [PostGIS Manual](https://postgis.net/documentation/)
- [Leaflet.js Docs](https://leafletjs.com/)
- [asyncpg Documentation](https://magicstack.github.io/asyncpg/)
- [Pydantic Documentation](https://docs.pydantic.dev/)

---

**Versión:** 2.0
**Última actualización:** Octubre 2025
**Autor:** Sistema de Monitoreo UNACH
