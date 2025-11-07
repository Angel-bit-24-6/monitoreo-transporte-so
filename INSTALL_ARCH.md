# Instalación en Arch Linux

Guía completa para instalar y ejecutar el sistema en Arch Linux.

---

## 📋 Requisitos

- Arch Linux (actualizado)
- Acceso sudo
- Conexión a Internet
- AUR helper (yay, paru, etc.) - opcional pero recomendado

---

## 🚀 Instalación Rápida (Script Automatizado)

```bash
cd /home/brian/monitoreo-transporte-so
chmod +x setup.sh
sudo ./setup.sh
```

El script detectará Arch Linux y usará `pacman` automáticamente.

**Tiempo estimado:** 10-15 minutos

---

## 🛠️ Instalación Manual Paso a Paso

### Paso 1: Actualizar Sistema

```bash
sudo pacman -Syu
```

### Paso 2: Instalar Dependencias

```bash
sudo pacman -S --needed \
    postgresql \
    postgis \
    python \
    python-pip \
    nodejs \
    npm \
    git \
    curl \
    wget \
    base-devel
```

**Nota:** En Arch Linux, `python` es Python 3 (actualmente 3.12+). El proyecto funciona con Python 3.11+.

### Paso 3: Instalar PostgreSQL y PostGIS

```bash
# Iniciar y habilitar servicio
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Inicializar base de datos (solo si es primera vez)
sudo -u postgres initdb -D /var/lib/postgres/data

# Reiniciar servicio
sudo systemctl restart postgresql
```

### Paso 4: Configurar PostgreSQL

```bash
# Crear base de datos y usuario
sudo -u postgres psql << EOF
CREATE USER app_user WITH PASSWORD 'transporte_pass_2024';
CREATE DATABASE transporte_db OWNER app_user;
\c transporte_db
CREATE EXTENSION postgis;
CREATE EXTENSION pgcrypto;
GRANT ALL PRIVILEGES ON DATABASE transporte_db TO app_user;
\q
EOF
```

### Paso 5: Aplicar Migraciones

```bash
cd /home/brian/monitoreo-transporte-so
sudo -u postgres psql -d transporte_db -f migrations/migrations_full_final_with_device_FIXED.sql
```

### Paso 6: Configurar Backend

```bash
cd backend

# Crear entorno virtual
python -m venv venv

# Activar
source venv/bin/activate

# Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt
```

### Paso 7: Crear Archivo .env

```bash
cat > .env << EOF
DATABASE_URL=postgresql://app_user:transporte_pass_2024@localhost:5432/transporte_db
DB_HOST=localhost
DB_PORT=5432
DB_NAME=transporte_db
DB_USER=app_user
DB_PASSWORD=transporte_pass_2024
DB_MIN_POOL_SIZE=10
DB_MAX_POOL_SIZE=50

HOST=0.0.0.0
PORT=8000
WORKERS=4
LOG_LEVEL=INFO
DEBUG=False

TOKEN_TTL_SECONDS=2592000
TOKEN_RENEWAL_THRESHOLD_MINUTES=10080
TOKEN_RENEWAL_CHECK_INTERVAL_SECONDS=3600
TOKEN_GRACE_PERIOD_DAYS=7
CLEANUP_TOKEN_DAYS=30

ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

WS_HEARTBEAT_INTERVAL=30
WS_TIMEOUT=300

OUT_OF_ROUTE_THRESHOLD_M=200
STOP_SPEED_THRESHOLD=1.5
STOP_TIME_THRESHOLD_S=120
SPEED_LIMIT_MS=22.22
EOF
```

### Paso 8: Iniciar Backend

```bash
# Asegúrate de tener venv activado
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verificar: http://localhost:8000/docs

### Paso 9: Configurar Frontend (Nueva terminal)

```bash
cd /home/brian/monitoreo-transporte-so/frontend

npm install
npm run dev
```

Verificar: http://localhost:5173

### Paso 10: Configurar Simulador (Nueva terminal)

```bash
cd /home/brian/monitoreo-transporte-so/simulator

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 🐳 Instalación con Docker

### Opción 1: Docker Compose

```bash
# Instalar Docker
sudo pacman -S docker docker-compose

# Iniciar servicio Docker
sudo systemctl start docker
sudo systemctl enable docker

# Agregar tu usuario al grupo docker (opcional, para no usar sudo)
sudo usermod -aG docker $USER
# Cerrar sesión y volver a entrar para aplicar cambios

# Iniciar servicios
docker-compose up -d --build

# Ver logs
docker-compose logs -f

# Aplicar migraciones
sleep 10
docker-compose exec postgres psql -U postgres -d transporte_db \
  -f /docker-entrypoint-initdb.d/migrations_full_final_with_device_FIXED.sql
```

### Verificar Servicios

```bash
docker-compose ps

# Debe mostrar:
# - postgres (healthy)
# - backend (running)
# - frontend (running)
```

---

## 📊 Crear Datos de Prueba

**✅ El sistema ya incluye:**
- 3 unidades de prueba (UNIT-001, UNIT-002, UNIT-003)
- 1 ruta precargada: **Ruta 1 - Tapachula Centro** (489 puntos GPS realistas)
- Rutas asignadas automáticamente a todas las unidades

Para verificar, consulta: http://localhost:8000/docs

**Si necesitas generar tokens adicionales:**

```bash
# Generar token para una unidad
curl -X POST http://localhost:8000/api/v1/tokens \
  -H "Content-Type: application/json" \
  -d '{
    "unidad_id": "UNIT-001",
    "device_id": "GPS-SIM-001",
    "ttl_seconds": 2592000,
    "revoke_old": false
  }'
```

Copiar el `token_plain` y configurar en `simulator/device_config.json`.

**Nota:** Para crear unidades o rutas adicionales, usa Swagger UI: http://localhost:8000/docs

---

## 🎮 Scripts de Ayuda

### start_backend.sh

```bash
#!/bin/bash
cd /home/brian/monitoreo-transporte-so/backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### start_frontend.sh

```bash
#!/bin/bash
cd /home/brian/monitoreo-transporte-so/frontend
npm run dev
```

### start_simulator.sh

```bash
#!/bin/bash
cd /home/brian/monitoreo-transporte-so/simulator
source venv/bin/activate
python gps_simulator_with_renewal.py -i 5
```

Hacer ejecutables:

```bash
chmod +x start_*.sh
```

---

## 🔧 Configuración como Servicio Systemd

### Backend Service

```bash
sudo nano /etc/systemd/system/transporte-backend.service
```

```ini
[Unit]
Description=Sistema de Monitoreo - Backend
After=network.target postgresql.service

[Service]
Type=simple
User=brian
WorkingDirectory=/home/brian/monitoreo-transporte-so/backend
Environment="PATH=/home/brian/monitoreo-transporte-so/backend/venv/bin"
ExecStart=/home/brian/monitoreo-transporte-so/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable transporte-backend
sudo systemctl start transporte-backend
sudo systemctl status transporte-backend
```

---

## 🐛 Solución de Problemas

### PostgreSQL no inicia

```bash
sudo systemctl status postgresql
sudo journalctl -u postgresql -n 50

# Si no está inicializado:
sudo -u postgres initdb -D /var/lib/postgres/data
sudo systemctl start postgresql
```

### Error de permisos Python

```bash
# Reinstalar en entorno virtual
deactivate
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Puerto en uso

```bash
# Ver qué usa el puerto 8000
sudo lsof -i :8000

# Matar proceso
kill -9 <PID>
```

### Python 3.11 específico (si es necesario)

Si necesitas Python 3.11 específicamente (aunque Python 3.12+ debería funcionar):

```bash
# Desde AUR
yay -S python311
# o
paru -S python311

# Luego usar python3.11 en lugar de python
python3.11 -m venv venv
```

---

## ✅ Checklist de Instalación

- [ ] PostgreSQL instalado y corriendo
- [ ] PostGIS instalado
- [ ] Python 3.11+ disponible
- [ ] Node.js instalado
- [ ] Base de datos creada
- [ ] Migraciones aplicadas
- [ ] Backend corriendo (http://localhost:8000/docs)
- [ ] Frontend corriendo (http://localhost:5173)
- [ ] Datos de prueba creados
- [ ] Simulador configurado

---

## 📞 Soporte

Ver logs:

```bash
# Backend
journalctl -u transporte-backend -f

# PostgreSQL
sudo journalctl -u postgresql -f

# Docker
docker-compose logs -f backend
```

---

## 🔍 Diferencias con Ubuntu/Debian

1. **Gestor de paquetes:** `pacman` en lugar de `apt`
2. **Python:** `python` en lugar de `python3.11` (Arch usa Python 3.12+)
3. **PostgreSQL:** Versión más reciente por defecto
4. **Inicialización de PostgreSQL:** Puede requerir `initdb` manualmente
5. **Rutas:** Ajustar rutas según tu instalación

---

**Última actualización:** Enero 2025

