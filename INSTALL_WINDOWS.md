# Instalación en Windows 11

Guía completa para instalar y ejecutar el sistema en Windows 11.

---

## 📋 Requisitos

- Windows 11 (o Windows 10)
- Python 3.11+ ([Descargar](https://www.python.org/downloads/))
- Node.js 18+ ([Descargar](https://nodejs.org/))
- PostgreSQL 14+ con PostGIS ([Descargar](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads))
- Git ([Descargar](https://git-scm.com/download/win))

---

## 🚀 Opción 1: Instalación con Docker Desktop (Recomendado)

### Paso 1: Instalar Docker Desktop

1. Descargar [Docker Desktop para Windows](https://www.docker.com/products/docker-desktop/)
2. Instalar y reiniciar
3. Abrir Docker Desktop y esperar que inicie

### Paso 2: Clonar el proyecto

```cmd
cd C:\Users\%USERNAME%\Documents
git clone <tu-repo> transporte
cd transporte\version_web
```

### Paso 3: Iniciar servicios con Docker

```cmd
docker-compose up -d --build
```

Esperar 30 segundos y verificar:

```cmd
docker-compose ps
```

### Paso 4: Aplicar migraciones

```cmd
docker-compose exec postgres psql -U postgres -d transporte_db -f /docker-entrypoint-initdb.d/migrations_full_final_with_device_FIXED.sql
```

### Paso 5: Acceder

- **Backend API**: http://localhost:8000/docs
- **Frontend Dashboard**: http://localhost:5173
- **PostgreSQL**: localhost:5432

**¡Listo!** Sistema funcionando con Docker.

---

## 🛠️ Opción 2: Instalación Nativa en Windows (Sin Docker)

### Paso 1: Instalar PostgreSQL

1. Descargar [PostgreSQL 14+](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads)
2. Durante instalación:
   - Usuario: `postgres`
   - Password: `tu_password` (anótalo)
   - Puerto: `5432`
   - Marcar **Stack Builder** para instalar PostGIS

3. Abrir Stack Builder y instalar:
   - **PostGIS Bundle**

### Paso 2: Crear Base de Datos

Abrir **SQL Shell (psql)** desde el menú de Windows:

```sql
-- Presionar Enter para valores por defecto hasta password
-- Ingresar tu password de postgres

CREATE DATABASE transporte_db;
\c transporte_db
CREATE EXTENSION postgis;
CREATE EXTENSION pgcrypto;
\q
```

### Paso 3: Aplicar Migraciones

```cmd
cd C:\Users\%USERNAME%\Documents\transporte\version_web

psql -U postgres -d transporte_db -f migrations\migrations_full_final_with_device_FIXED.sql
```

Ingresar password cuando lo solicite.

### Paso 4: Configurar Backend

```cmd
cd backend

REM Crear entorno virtual
python -m venv venv

REM Activar entorno virtual
venv\Scripts\activate

REM Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt
```

### Paso 5: Configurar Variables de Entorno

Crear archivo `backend\.env`:

```env
DATABASE_URL=postgresql://app_user:TU_PASSWORD@localhost:5432/transporte_db
DB_HOST=localhost
DB_PORT=5432
DB_NAME=transporte_db
DB_USER=app_user
DB_PASSWORD=TU_PASSWORD
DB_MIN_POOL_SIZE=10
DB_MAX_POOL_SIZE=50

HOST=0.0.0.0
PORT=8000
WORKERS=4
LOG_LEVEL=INFO
DEBUG=False

TOKEN_EXPIRY_DAYS=30
CLEANUP_TOKEN_DAYS=30

ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

WS_HEARTBEAT_INTERVAL=30
WS_TIMEOUT=300

OUT_OF_ROUTE_THRESHOLD_M=200
STOP_SPEED_THRESHOLD=1.5
STOP_TIME_THRESHOLD_S=120
```

**⚠️ IMPORTANTE**: Reemplazar `TU_PASSWORD` con tu password de PostgreSQL.

### Paso 6: Iniciar Backend

```cmd
REM Asegúrate de estar en backend\ con venv activado
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verificar: http://localhost:8000/docs

### Paso 7: Configurar Frontend (Nueva terminal)

```cmd
cd C:\Users\%USERNAME%\Documents\transporte\version_web\frontend

npm install

npm run dev
```

Verificar: http://localhost:5173

### Paso 8: Configurar Simulador (Nueva terminal)

```cmd
cd C:\Users\%USERNAME%\Documents\transporte\version_web\simulator

REM Crear entorno virtual
python -m venv venv

REM Activar
venv\Scripts\activate

REM Instalar dependencias
pip install -r requirements.txt
```

---

## 🎮 Scripts de Ayuda (Batch Files)

Para facilitar el inicio, usa los archivos `.bat` incluidos:

### `start_backend.bat`
```cmd
start_backend.bat
```

Inicia el backend automáticamente.

### `start_frontend.bat`
```cmd
start_frontend.bat
```

Inicia el frontend automáticamente.

### `start_simulator.bat`
```cmd
start_simulator.bat
```

Inicia el simulador GPS.

### `start_all.bat`
```cmd
start_all.bat
```

Inicia todo a la vez (backend, frontend, simulador).

---

## 📊 Crear Datos de Prueba

### 1. Crear Unidades

Abrir **PowerShell** o **CMD**:

```cmd
curl -X POST http://localhost:8000/api/v1/unidades ^
  -H "Content-Type: application/json" ^
  -d "{\"id\":\"UNIT-001\",\"placa\":\"ABC-123\",\"chofer\":\"Juan Pérez\",\"activo\":true}"

curl -X POST http://localhost:8000/api/v1/unidades ^
  -H "Content-Type: application/json" ^
  -d "{\"id\":\"UNIT-002\",\"placa\":\"DEF-456\",\"chofer\":\"María López\",\"activo\":true}"

curl -X POST http://localhost:8000/api/v1/unidades ^
  -H "Content-Type: application/json" ^
  -d "{\"id\":\"UNIT-003\",\"placa\":\"GHI-789\",\"chofer\":\"Carlos Ruiz\",\"activo\":true}"
```

### 2. Verificar Ruta Precargada

**✅ El sistema ya incluye una ruta de ejemplo:**
- **Nombre:** Ruta 1 - Tapachula Centro
- **Puntos:** 489 coordenadas GPS realistas
- **Estado:** Ya asignada automáticamente a todas las unidades activas

Puedes verificarla en: http://localhost:8000/docs → `GET /api/v1/rutas`

**Nota:** Si necesitas crear rutas adicionales, consulta la [documentación de API REST](README.md#api-rest) o usa Swagger UI.

### 3. Generar Tokens

```cmd
curl -X POST http://localhost:8000/api/v1/tokens ^
  -H "Content-Type: application/json" ^
  -d "{\"unidad_id\":\"UNIT-001\",\"device_id\":\"GPS-SIM-001\",\"ttl_seconds\":2592000,\"revoke_old\":false}"
```

**⚠️ Copiar el `token_plain` de la respuesta.**

### 4. Configurar Simulador

Editar `simulator\device_config.json`:

```json
{
  "server_url": "ws://localhost:8000/ws/device",
  "devices": [
    {
      "unidad_id": "UNIT-001",
      "device_id": "GPS-SIM-001",
      "token": "TU_TOKEN_AQUI",
      "token_expires_at": null
    },
    {
      "unidad_id": "UNIT-002",
      "device_id": "GPS-SIM-002",
      "token": "TU_TOKEN_AQUI_2",
      "token_expires_at": null
    },
    {
      "unidad_id": "UNIT-003",
      "device_id": "GPS-SIM-003",
      "token": "TU_TOKEN_AQUI_3",
      "token_expires_at": null
    }
  ]
}
```

### 5. Ejecutar Simulador

```cmd
cd simulator
venv\Scripts\activate
python gps_simulator_with_renewal.py -i 5
```

---

## 🐛 Solución de Problemas en Windows

### Error: "python no se reconoce como comando"

**Solución:**
1. Reinstalar Python marcando "Add Python to PATH"
2. O agregar manualmente:
   - Abrir "Variables de entorno"
   - Agregar `C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311` a PATH

### Error: "psql no se reconoce como comando"

**Solución:**
Agregar PostgreSQL a PATH:
- Agregar `C:\Program Files\PostgreSQL\14\bin` a PATH

### Error: "No module named 'app'"

**Solución:**
Asegúrate de estar en el directorio correcto y con venv activado:
```cmd
cd backend
venv\Scripts\activate
python -c "import app"
```

### Error de conexión a PostgreSQL

**Solución:**
1. Verificar que PostgreSQL esté corriendo:
   - Abrir "Servicios" (Win + R, escribir `services.msc`)
   - Buscar "postgresql-x64-14"
   - Debe estar "Ejecutándose"

2. Verificar credenciales en `.env`

3. Test de conexión:
```cmd
psql -U postgres -d transporte_db -c "SELECT 1;"
```

### Puerto 8000 ya en uso

**Solución:**
```cmd
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

---

## 📁 Estructura de Directorios en Windows

```
C:\Users\TuNombre\Documents\transporte\version_web\
├── backend\
│   ├── venv\                    # Entorno virtual Python
│   ├── app\                     # Código backend
│   ├── .env                     # Configuración (CREAR)
│   └── requirements.txt
├── frontend\
│   ├── node_modules\
│   ├── src\
│   └── package.json
├── simulator\
│   ├── venv\                    # Entorno virtual Python
│   ├── gps_simulator_with_renewal.py  # Simulador con renovación automática
│   └── device_config.json       # Configuración de dispositivos
├── migrations\
│   └── migrations_full_final_with_device_FIXED.sql
├── start_backend.bat            # Script inicio backend
├── start_frontend.bat           # Script inicio frontend
├── start_simulator.bat          # Script inicio simulador
└── start_all.bat                # Inicia todo
```

---

## ✅ Checklist de Instalación

- [ ] PostgreSQL instalado con PostGIS
- [ ] Python 3.11+ instalado
- [ ] Node.js 18+ instalado
- [ ] Base de datos `transporte_db` creada
- [ ] Extensiones PostGIS y pgcrypto instaladas
- [ ] Migraciones SQL aplicadas
- [ ] Backend configurado con `.env`
- [ ] Backend iniciando correctamente (http://localhost:8000/docs)
- [ ] Frontend instalado y corriendo (http://localhost:5173)
- [ ] Unidades de prueba creadas
- [ ] Rutas de prueba creadas
- [ ] Tokens generados para simulador
- [ ] Simulador configurado con tokens

---

## 🔐 Notas de Seguridad

1. **Nunca subas `.env` a GitHub**
2. Cambia passwords por defecto en producción
3. Los tokens se muestran UNA sola vez, guárdalos
4. Usa `.gitignore` incluido en el proyecto

---

## 🎓 Comandos Útiles Windows

```cmd
REM Ver procesos Python
tasklist | findstr python

REM Matar proceso
taskkill /F /PID <pid>

REM Ver puertos en uso
netstat -ano | findstr :8000

REM Limpiar cache pip
pip cache purge

REM Reinstalar dependencias
pip install -r requirements.txt --force-reinstall
```

---

## 📞 ¿Necesitas Ayuda?

1. Revisar logs del backend
2. Revisar logs del frontend (consola del navegador F12)
3. Verificar que PostgreSQL esté corriendo
4. Crear issue en GitHub con logs completos

---

**Última actualización:** Octubre 2025
