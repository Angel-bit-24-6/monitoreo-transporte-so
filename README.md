# Sistema de Monitoreo de Transporte y Seguridad Vial

**ODS 11: Ciudades y Comunidades Sostenibles**

---

🌎 **Audio contextual ODS 11 - México:**

<audio controls>
  <source src="https://github.com/Angel-bit-24-6/monitoreo-transporte-so/raw/refs/heads/main/frontend/public/audio/ODS11_Ciudades_AnalisisM%C3%A9xico.mp3" type="audio/mp3">
  Tu navegador no soporta el elemento de audio.
</audio>

> Escucha una introducción sobre la importancia de la ODS 11 y su impacto en la movilidad urbana sostenible en México.

---

Sistema completo de monitoreo en tiempo real para transporte público que permite rastrear vehículos, detectar anomalías y generar alertas automáticas.

---

## 🚀 Inicio Rápido

**¿Primera vez?** → Lee [QUICK_START.md](QUICK_START.md)

**Documentación por Sistema Operativo:**
- 🪟 [Instalación en Windows](INSTALL_WINDOWS.md)
- 🐧 [Instalación en Ubuntu/Linux](INSTALL_UBUNTU.md)
- 🚢 [Deployment en Producción](DEPLOYMENT.md)

**Scripts de Inicio:**
- Windows: `start_backend.bat`, `start_frontend.bat`, `start_simulator.bat`
- Linux: `start_backend.sh`, `start_frontend.sh`, `start_simulator.sh`

---

## 📋 Tabla de Contenidos

- [Características](#características)
- [Arquitectura](#arquitectura)
- [Tecnologías](#tecnologías)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Uso](#uso)
- [API REST](#api-rest)
- [Protocolo WebSocket](#protocolo-websocket)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Desarrollo](#desarrollo)

## 📚 Documentación Técnica Detallada

Para información técnica profunda, consulta:

- **[docs/ARQUITECTURA.md](docs/ARQUITECTURA.md)** - Diseño del sistema, flujos de datos, componentes
- **[docs/TOKEN_SYSTEM.md](docs/TOKEN_SYSTEM.md)** - Sistema completo de autenticación y tokens
- **[docs/EVENTOS.md](docs/EVENTOS.md)** - Sistema de detección automática de eventos

---

## Características

### Funcionalidades Principales

✅ **Monitoreo en Tiempo Real**
- Recepción de posiciones GPS cada 5-10 segundos
- Visualización de unidades en mapa interactivo (Leaflet.js)
- Estados de conexión en tiempo real

✅ **Detección Automática de Eventos**
- **OUT_OF_BOUND**: Desviación de ruta (> 200m)
- **STOP_LONG**: Detención prolongada (> 120s)
- **SPEEDING**: Exceso de velocidad (configurable)

✅ **Autenticación Segura**
- Tokens SHA-256 hasheados (nunca en texto plano)
- Multi-token: múltiples dispositivos por unidad
- Multi-device: identificación por device_id
- Rotación y revocación de tokens

✅ **API REST Completa**
- CRUD de unidades, rutas y asignaciones
- Consulta de eventos históricos
- Estadísticas y reportes
- Documentación automática (Swagger/ReDoc)

✅ **WebSocket Bidireccional**
- Dispositivos GPS → Servidor (posiciones)
- Servidor → Dashboards (updates en tiempo real)
- Sistema de suscripciones por unidad
- Reconexión automática

✅ **Sistema de Puntos de Interés (POIs)**
- 22 POIs precargados en Tapachula, Chiapas
- 5 categorías: Hospitales, Farmacias, Papelerías, Gasolineras, Bancos
- Visualización en mapa con iconos personalizados
- API REST para consultar, buscar por nombre y ubicaciones cercanas

✅ **Chatbot Inteligente**
- Asistente virtual con procesamiento de lenguaje natural
- Búsqueda de POIs por categoría, nombre o cercanía
- Integración visual con mapa (resaltado automático)
- WebSocket dedicado para respuestas en tiempo real
- Sugerencias rápidas y comandos intuitivos

---

## Arquitectura

```
┌─────────────────┐          ┌──────────────────┐          ┌─────────────────┐
│  Dispositivo    │  WebSocket│                  │          │                 │
│  GPS (Cliente)  ├──────────►│  Backend FastAPI │◄─────────┤  Dashboard Web  │
│                 │  POS msg  │                  │ WebSocket│                 │
└─────────────────┘           │  - Auth Service  │          └─────────────────┘
                              │  - Position Svc  │
                              │  - WebSocket Mgr │
                              │                  │
                              └────────┬─────────┘
                                       │
                                       ▼
                              ┌─────────────────┐
                              │  PostgreSQL +   │
                              │    PostGIS      │
                              │                 │
                              │  - Unidades     │
                              │  - Posiciones   │
                              │  - Eventos      │
                              │  - Rutas        │
                              └─────────────────┘
```

### Flujo de Datos

1. **Dispositivo GPS** se autentica con token
2. Envía posiciones periódicas via WebSocket
3. **Backend** valida, persiste en PostgreSQL
4. Ejecuta función PL/pgSQL `fn_insert_position_and_detect`
5. Calcula distancia a ruta, detecta eventos
6. Envía ACK al dispositivo + broadcast a dashboards
7. **Dashboard** recibe updates en tiempo real y los visualiza

---

## Tecnologías

### Backend
- **Python 3.11+**
- **FastAPI** - Framework web async
- **asyncpg** - Driver PostgreSQL async
- **Pydantic** - Validación de datos
- **structlog** - Logging estructurado
- **websockets** - Comunicación bidireccional

### Frontend
- **HTML/CSS/JavaScript** (Vanilla)
- **Vite** - Build tool
- **Leaflet.js** - Mapas interactivos
- **WebSocket API** - Conexión en tiempo real

### Base de Datos
- **PostgreSQL 14+**
- **PostGIS** - Extensión geoespacial
- **pgcrypto** - Funciones de hashing

### DevOps
- **Docker & Docker Compose**
- **Uvicorn** - Servidor ASGI

---

## Requisitos

### 💻 Sistema Operativo

Este proyecto funciona en **Windows, Linux y macOS**.

**Guías específicas por sistema:**
- 🪟 **Windows 11/10** → Ver [INSTALL_WINDOWS.md](INSTALL_WINDOWS.md)
- 🐧 **Ubuntu/Linux** → Ver [INSTALL_UBUNTU.md](INSTALL_UBUNTU.md)
- 🐳 **Docker** (cualquier OS) → Continuar leyendo

### Desarrollo Local

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+ con PostGIS
- Git

### Con Docker (Recomendado - Multiplataforma)

- Docker Desktop (Windows/Mac) o Docker Engine (Linux)
- Docker Compose 2.0+

---

## Instalación

### ⚡ Instalación Rápida por Sistema Operativo

**🪟 Windows:**
```cmd
REM Opción 1: Con Docker Desktop
docker-compose up -d --build

REM Opción 2: Nativo (ver INSTALL_WINDOWS.md)
start_backend.bat
start_frontend.bat
start_simulator.bat
```

**🐧 Ubuntu/Linux:**
```bash
# Opción 1: Script automático
chmod +x setup.sh
sudo ./setup.sh

# Opción 2: Con Docker
docker-compose up -d --build

# Opción 3: Scripts manuales
chmod +x start_*.sh
./start_backend.sh
./start_frontend.sh
./start_simulator.sh
```

### Opción 1: Docker Compose (Recomendado - Funciona en Windows, Linux, Mac)

```bash
# 1. Clonar repositorio
cd version_web

# 2. Aplicar migraciones SQL manualmente
psql -U postgres -d transporte_db -f migrations/migrations_full_final_with_device_FIXED.sql

# 3. Iniciar servicios
docker-compose up -d

# 4. Verificar logs
docker-compose logs -f backend
```

**Servicios disponibles:**
- Backend: http://localhost:8000
- Frontend: http://localhost:5173
- PostgreSQL: localhost:5432

---

### Opción 2: Desarrollo Local

#### 1. Base de Datos

```bash
# Crear base de datos
createdb transporte_db

# Instalar PostGIS
psql -d transporte_db -c "CREATE EXTENSION postgis;"
psql -d transporte_db -c "CREATE EXTENSION pgcrypto;"

# Aplicar migraciones
psql -U postgres -d transporte_db -f migrations/migrations_full_final_with_device_FIXED.sql
```

#### 2. Backend

```bash
cd backend

# Crear entorno virtual
python -m venv venv

# Activar (Windows)
venv\Scripts\activate
# Activar (Linux/Mac)
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Copiar archivo de configuración
cp .env.example .env
# Editar .env con tus credenciales de base de datos

# Iniciar servidor
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 3. Frontend

```bash
cd frontend

# Instalar dependencias
npm install

# Iniciar servidor de desarrollo
npm run dev
```

**Frontend disponible en:** http://localhost:5173

#### 4. Simulador (Opcional)

```bash
cd simulator

# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar tokens en device_config.json
# Editar simulator/device_config.json con tokens válidos

# Ver opciones
python gps_simulator_with_renewal.py --help

# Ejecutar simulador (lee config desde device_config.json)
python gps_simulator_with_renewal.py -i 5
```

**💡 Tip:** Usa los scripts de inicio que manejan el venv automáticamente:
- Windows: `start_simulator.bat`
- Linux: `./start_simulator.sh`

---

## Configuración

### Variables de Entorno (Backend)

Archivo: `backend/.env`

```env
# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/transporte_db
DB_HOST=localhost
DB_PORT=5432
DB_NAME=transporte_db
DB_USER=postgres
DB_PASSWORD=your_secure_password
DB_MIN_POOL_SIZE=10
DB_MAX_POOL_SIZE=50

# Server
HOST=0.0.0.0
PORT=8000
WORKERS=4
LOG_LEVEL=INFO
DEBUG=False

# Token
TOKEN_EXPIRY_DAYS=30
CLEANUP_TOKEN_DAYS=30

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

# WebSocket
WS_HEARTBEAT_INTERVAL=30
WS_TIMEOUT=300

# Sistema Config (umbrales)
OUT_OF_ROUTE_THRESHOLD_M=200
STOP_SPEED_THRESHOLD=1.5
STOP_TIME_THRESHOLD_S=120
```

---

## Uso

### ✅ Datos Precargados

El sistema incluye datos de prueba listos para usar:
- **3 Unidades:** UNIT-001, UNIT-002, UNIT-003
- **1 Ruta:** Ruta 1 - Tapachula Centro (489 puntos GPS realistas)
- **Asignaciones:** Todas las unidades tienen la ruta asignada automáticamente

Verifica en: http://localhost:8000/docs

---

### 1. Generar Token para Dispositivo

```bash
curl -X POST http://localhost:8000/api/v1/tokens \
  -H "Content-Type: application/json" \
  -d '{
    "unidad_id": "UNIT-001",
    "device_id": "GPS-001",
    "ttl_seconds": 2592000,
    "revoke_old": false
  }'
```

**Respuesta:**
```json
{
  "token_plain": "abc123def456...",
  "token_id": 1,
  "unidad_id": "UNIT-001",
  "device_id": "GPS-001",
  "expires_at": "2025-11-13T...",
  "message": "Token creado exitosamente. Guárdalo de forma segura..."
}
```

⚠️ **IMPORTANTE**: Guardar el `token_plain`, no se mostrará nuevamente.

### 2. Conectar Simulador

Editar `simulator/device_config.json`:

```json
{
  "server_url": "ws://localhost:8000/ws/device",
  "devices": [
    {
      "unidad_id": "UNIT-001",
      "device_id": "GPS-001",
      "token": "TU_TOKEN_AQUI",
      "token_expires_at": null
    }
  ]
}
```

Ejecutar:
```bash
python gps_simulator_with_renewal.py -i 5
```

### 3. Abrir Dashboard

Ir a: **http://localhost:5173**

---

### 📝 (Opcional) Crear Datos Adicionales

Si necesitas crear más unidades o rutas, usa la API REST:

**Crear una unidad adicional:**
```bash
curl -X POST http://localhost:8000/api/v1/unidades \
  -H "Content-Type: application/json" \
  -d '{
    "id": "UNIT-004",
    "placa": "XYZ-999",
    "chofer": "Ana García",
    "activo": true
  }'
```

**Crear una ruta adicional:**
```bash
curl -X POST http://localhost:8000/api/v1/rutas \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Ruta 2 - Norte",
    "descripcion": "Ruta secundaria",
    "coordinates": [
      [-92.2700, 14.9200],
      [-92.2680, 14.9180],
      [-92.2660, 14.9160]
    ]
  }'
```

**Asignar ruta a unidad:**
```bash
curl -X POST http://localhost:8000/api/v1/rutas/assignments \
  -H "Content-Type: application/json" \
  -d '{
    "unidad_id": "UNIT-004",
    "ruta_id": 2,
    "start_ts": "2025-10-19T00:00:00Z"
  }'
```

Para más opciones, consulta la [documentación de API REST](#api-rest) o usa Swagger UI: http://localhost:8000/docs

---

## API REST

### Documentación Interactiva

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Endpoints Principales

#### Unidades
- `GET /api/v1/unidades` - Listar unidades
- `GET /api/v1/unidades/{id}` - Obtener detalles
- `POST /api/v1/unidades` - Crear unidad
- `PATCH /api/v1/unidades/{id}` - Actualizar
- `DELETE /api/v1/unidades/{id}` - Eliminar
- `GET /api/v1/unidades/{id}/posiciones` - Posiciones históricas

#### Tokens
- `POST /api/v1/tokens` - Crear token
- `DELETE /api/v1/tokens/revoke` - Revocar token
- `DELETE /api/v1/tokens/device/{unidad_id}/{device_id}` - Revocar todos

#### Rutas
- `GET /api/v1/rutas` - Listar rutas
- `GET /api/v1/rutas/{id}` - Detalles con GeoJSON
- `POST /api/v1/rutas` - Crear ruta
- `POST /api/v1/rutas/assignments` - Asignar a unidad

#### Eventos
- `GET /api/v1/eventos` - Listar con filtros
- `GET /api/v1/eventos/{id}` - Detalles
- `GET /api/v1/eventos/stats/summary` - Estadísticas

#### POIs (Puntos de Interés)
- `GET /api/v1/pois` - Listar POIs (filtro por categoría opcional)
- `GET /api/v1/pois/{id}` - Obtener detalles de un POI
- `GET /api/v1/pois/buscar` - Buscar POIs por nombre (parámetro `q`)
- `GET /api/v1/pois/cercanos` - POIs cercanos a coordenadas (lat, lon, radio)

#### Sistema
- `GET /api/v1/health` - Health check
- `GET /api/v1/status` - Estado detallado

---

## Protocolo WebSocket

### Endpoint Dispositivos: `ws://localhost:8000/ws/device`

#### 1. Autenticación (Cliente → Servidor)
```json
{
  "type": "AUTH",
  "token": "abc123def456...",
  "device_id": "GPS-001"
}
```

**Respuesta Exitosa:**
```json
{
  "type": "AUTH_OK",
  "unidad_id": "UNIT-001",
  "message": "Autenticación exitosa"
}
```

#### 2. Enviar Posición (Cliente → Servidor)
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

**Respuesta ACK:**
```json
{
  "type": "ACK",
  "posicion_id": 45678,
  "event_id": 123,
  "timestamp": "2025-10-14T10:30:01Z"
}
```

### Endpoint Dashboard: `ws://localhost:8000/ws/dashboard`

#### 1. Suscribirse a Unidades (Cliente → Servidor)
```json
{
  "type": "SUBSCRIBE",
  "unidad_ids": ["UNIT-001", "UNIT-002"]
}
```

#### 2. Update de Posición (Servidor → Cliente)
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

#### 3. Alerta de Evento (Servidor → Cliente)
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

### Endpoint Chatbot: `ws://localhost:8000/ws/chatbot`

#### 1. Enviar Mensaje (Cliente → Servidor)
```json
{
  "type": "USER_MESSAGE",
  "message": "Hospitales cercanos"
}
```

#### 2. Respuesta del Bot (Servidor → Cliente)
```json
{
  "type": "BOT_MESSAGE",
  "message": "🏥 **Hospitales encontrados** (4):\n\n1. Hospital General...",
  "timestamp": "2025-10-14T10:30:00Z",
  "data": {
    "action": "highlight_pois",
    "pois": [
      {
        "id": 1,
        "nombre": "Hospital General",
        "lat": 14.9067,
        "lon": -92.2631,
        "categoria": "hospital",
        "direccion": "Calle Principal 123",
        "telefono": "961-123-4567",
        "horario": "24 horas"
      }
    ],
    "zoom_to_fit": true
  }
}
```

**Comandos soportados:**
- "Hospitales cercanos" - Buscar POIs cercanos
- "Farmacias" - Listar POIs por categoría
- "Busca BBVA" - Buscar POI por nombre
- "¿Qué categorías hay?" - Ver categorías disponibles
- "Ayuda" - Ver guía de uso

---

## Estructura del Proyecto

```
version_web/
├── backend/                    # Backend FastAPI
│   ├── app/
│   │   ├── api/               # Endpoints REST
│   │   │   ├── __init__.py
│   │   │   ├── unidades.py
│   │   │   ├── tokens.py
│   │   │   ├── rutas.py
│   │   │   ├── eventos.py
│   │   │   ├── pois.py          # Endpoints de POIs
│   │   │   └── health.py
│   │   ├── core/              # Configuración y DB
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   └── database.py
│   │   ├── models/            # Schemas Pydantic
│   │   │   ├── __init__.py
│   │   │   └── schemas.py
│   │   ├── services/          # Lógica de negocio
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py
│   │   │   └── position_service.py
│   │   ├── websockets/        # Handlers WebSocket
│   │   │   ├── __init__.py
│   │   │   ├── connection_manager.py
│   │   │   ├── device_handler.py
│   │   │   ├── dashboard_handler.py
│   │   │   └── chatbot_handler.py  # Chatbot inteligente
│   │   └── main.py            # App principal
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
│
├── frontend/                   # Dashboard web
│   ├── src/
│   │   └── main.js            # App JavaScript
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile
│
├── simulator/                  # Simulador GPS
│   ├── gps_simulator_with_renewal.py  # Simulador con renovación automática
│   ├── device_config.json      # Configuración de dispositivos y tokens
│   └── requirements.txt
│
├── migrations/                 # Migraciones SQL
│   └── migrations_full_final_with_device_FIXED.sql  # Incluye tabla POI
│
├── docs/                       # Documentación adicional
│
├── docker-compose.yml
├── .gitignore
└── README.md
```

---

## Desarrollo

### Ejecutar Tests

```bash
# Backend
cd backend
pytest

# Con cobertura
pytest --cov=app --cov-report=html
```

### Linting y Formato

```bash
# Backend
black app/
isort app/
flake8 app/

# Frontend
npm run lint
```

### Ver Logs

```bash
# Docker
docker-compose logs -f backend
docker-compose logs -f frontend

# Local
tail -f backend/logs/app.log
```

---

## 🤝 Contribuciones

1. Fork el repositorio
2. Crear rama feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -m 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abrir Pull Request

---

## 📄 Licencia

Este proyecto es parte del curso de Sistemas Operativos - UNACH

---

## 👥 Autores

- **DevPilots** - Estudiantes 7° Semestre
- Universidad Nacional de Chimborazo (UNACH)
- Sistemas Operativos - 2025

---

## 🆘 Soporte

Para problemas o preguntas:
1. Revisar [Issues](../../issues)
2. Crear nuevo Issue con detalles completos
3. Incluir logs y pasos para reproducir

---

## 📚 Referencias

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [PostGIS Manual](https://postgis.net/documentation/)
- [Leaflet.js Docs](https://leafletjs.com/)
- [WebSocket Protocol](https://datatracker.ietf.org/doc/html/rfc6455)
