# Instalación en Ubuntu/Linux

Guía completa para instalar y ejecutar el sistema en Ubuntu 20.04+, Debian 11+, o distribuciones similares.

---

## 📋 Requisitos

- Ubuntu 20.04+ o Debian 11+
- Acceso sudo
- Conexión a Internet

---

## 🚀 Instalación Rápida (Script Automatizado)

```bash
cd version_web
chmod +x setup.sh
sudo ./setup.sh
```

El script instalará automáticamente:
- PostgreSQL 14 + PostGIS
- Python 3.11
- Node.js
- Backend configurado
- Base de datos con datos de prueba
- Tokens generados

**Tiempo estimado:** 10-15 minutos

---

## 🛠️ Instalación Manual Paso a Paso

### Paso 1: Actualizar Sistema

```bash
sudo apt update
sudo apt upgrade -y
```

### Paso 2: Instalar Dependencias

```bash
sudo apt install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    postgresql-14 \
    postgresql-14-postgis-3 \
    postgresql-contrib \
    nodejs \
    npm \
    git \
    curl \
    wget
```

### Paso 3: Configurar PostgreSQL

```bash
# Iniciar servicio
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Crear base de datos
sudo -u postgres psql << EOF
CREATE DATABASE transporte_db;
\c transporte_db
CREATE EXTENSION postgis;
CREATE EXTENSION pgcrypto;
\q
EOF
```

### Paso 4: Aplicar Migraciones

```bash
cd version_web
sudo -u postgres psql -d transporte_db -f migrations/migrations_full_final_with_device.sql
```

### Paso 5: Configurar Backend

```bash
cd backend

# Crear entorno virtual
python3.11 -m venv venv

# Activar
source venv/bin/activate

# Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt
```

### Paso 6: Crear Archivo .env

```bash
cp .env.example .env
nano .env
```

Editar con tus valores:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/transporte_db
DB_HOST=localhost
DB_PORT=5432
DB_NAME=transporte_db
DB_USER=postgres
DB_PASSWORD=postgres
# ... resto de configuración
```

### Paso 7: Iniciar Backend

```bash
# Asegúrate de tener venv activado
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verificar: http://localhost:8000/docs

### Paso 8: Configurar Frontend (Nueva terminal)

```bash
cd ../frontend

npm install
npm run dev
```

Verificar: http://localhost:5173

### Paso 9: Configurar Simulador (Nueva terminal)

```bash
cd ../simulator

python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 🐳 Instalación con Docker

### Opción 1: Docker Compose

```bash
# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Instalar Docker Compose
sudo apt install docker-compose-plugin

# Iniciar servicios
docker-compose up -d --build

# Ver logs
docker-compose logs -f

# Aplicar migraciones
sleep 10
docker-compose exec postgres psql -U postgres -d transporte_db \
  -f /docker-entrypoint-initdb.d/migrations_full_final_with_device.sql
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
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### start_frontend.sh

```bash
#!/bin/bash
cd frontend
npm run dev
```

### start_simulator.sh

```bash
#!/bin/bash
cd simulator
source venv/bin/activate
python3 gps_simulator_with_renewal.py -i 5
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
User=tu_usuario
WorkingDirectory=/ruta/completa/version_web/backend
Environment="PATH=/ruta/completa/version_web/backend/venv/bin"
ExecStart=/ruta/completa/version_web/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
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
```

### Error de permisos Python

```bash
# Reinstalar en entorno virtual
deactivate
rm -rf venv
python3.11 -m venv venv
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
sudo tail -f /var/log/postgresql/postgresql-14-main.log

# Docker
docker-compose logs -f backend
```

---

**Última actualización:** Octubre 2025
