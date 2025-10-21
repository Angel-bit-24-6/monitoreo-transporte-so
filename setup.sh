#!/bin/bash

# Script de setup automatizado para Sistema de Monitoreo de Transporte
# Compatible con: Ubuntu 20.04+, Debian 11+

set -e

echo "=========================================="
echo "  Sistema de Monitoreo de Transporte"
echo "  Setup Automatizado v1.0"
echo "=========================================="
echo ""

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

# Verificar si se ejecuta como root
if [[ $EUID -ne 0 ]]; then
   print_error "Este script debe ejecutarse como root (sudo)"
   exit 1
fi

echo "1. Actualizando sistema..."
apt update -qq
apt upgrade -y -qq
print_success "Sistema actualizado"

echo ""
echo "2. Instalando dependencias del sistema..."
apt install -y -qq \
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

print_success "Dependencias instaladas"

echo ""
echo "3. Configurando PostgreSQL..."
systemctl start postgresql
systemctl enable postgresql

# Generar password seguro
DB_PASSWORD=$(openssl rand -base64 32 | tr -dc 'A-Za-z0-9' | head -c 20)

sudo -u postgres psql -c "DROP DATABASE IF EXISTS transporte_db;" 2>/dev/null || true
sudo -u postgres psql -c "DROP USER IF EXISTS app_user;" 2>/dev/null || true

sudo -u postgres psql << EOF
CREATE USER app_user WITH PASSWORD '$DB_PASSWORD';
CREATE DATABASE transporte_db OWNER app_user;
\c transporte_db
CREATE EXTENSION postgis;
CREATE EXTENSION pgcrypto;
GRANT ALL PRIVILEGES ON DATABASE transporte_db TO app_user;
EOF

print_success "PostgreSQL configurado"
print_info "Usuario: app_user"
print_info "Password: $DB_PASSWORD"
print_info "Base de datos: transporte_db"

# Guardar credenciales
echo "$DB_PASSWORD" > /tmp/db_password.txt
chmod 600 /tmp/db_password.txt

echo ""
echo "4. Aplicando migraciones SQL..."
if [ -f "migrations/migrations_full_final_with_device_FIXED.sql" ]; then
    sudo -u postgres psql -d transporte_db -f migrations/migrations_full_final_with_device_FIXED.sql
    print_success "Migraciones aplicadas"
else
    print_error "No se encontró el archivo de migraciones"
    exit 1
fi

echo ""
echo "5. Configurando Backend..."
cd backend

# Crear usuario del sistema
if ! id "appuser" &>/dev/null; then
    useradd -m -s /bin/bash appuser
    print_success "Usuario del sistema creado: appuser"
fi

# Setup virtual environment
sudo -u appuser python3.11 -m venv venv
sudo -u appuser bash -c "source venv/bin/activate && pip install --upgrade pip -q && pip install -r requirements.txt -q"
print_success "Entorno virtual creado y dependencias instaladas"

# Crear archivo .env solo si NO existe
if [ ! -f .env ]; then
cat > .env << EOF
DATABASE_URL=postgresql://app_user:$DB_PASSWORD@localhost:5432/transporte_db
DB_HOST=localhost
DB_PORT=5432
DB_NAME=transporte_db
DB_USER=app_user
DB_PASSWORD=$DB_PASSWORD
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
chmod 600 .env
chown appuser:appuser .env
print_success "Archivo .env creado automáticamente"
else
print_info "Archivo .env ya existe, no se reemplaza"
fi

cd ..

echo ""
echo "6. Configurando Frontend..."
cd frontend

# Instalar dependencias
npm install -q
print_success "Dependencias de frontend instaladas"

cd ..

echo ""
echo "7. Creando servicios systemd..."

# Servicio para backend
cat > /etc/systemd/system/transporte-backend.service << EOF
[Unit]
Description=Sistema de Monitoreo de Transporte - Backend
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=appuser
WorkingDirectory=$(pwd)/backend
Environment="PATH=$(pwd)/backend/venv/bin"
ExecStart=$(pwd)/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable transporte-backend.service
print_success "Servicio backend creado"

echo ""
echo "8. Iniciando servicios..."
systemctl start transporte-backend.service
sleep 3

if systemctl is-active --quiet transporte-backend.service; then
    print_success "Backend iniciado correctamente"
else
    print_error "Error al iniciar backend"
    systemctl status transporte-backend.service --no-pager
fi

echo ""
echo "9. Generando tokens para simulador..."

TOKEN_1=$(curl -s -X POST http://localhost:8000/api/v1/tokens \
  -H "Content-Type: application/json" \
  -d '{
    "unidad_id": "UNIT-001",
    "device_id": "GPS-DEVICE-001",
    "ttl_seconds": 2592000,
    "revoke_old": false
  }' | jq -r '.token_plain')

TOKEN_2=$(curl -s -X POST http://localhost:8000/api/v1/tokens \
  -H "Content-Type: application/json" \
  -d '{
    "unidad_id": "UNIT-002",
    "device_id": "GPS-DEVICE-002",
    "ttl_seconds": 2592000,
    "revoke_old": false
  }' | jq -r '.token_plain')

TOKEN_3=$(curl -s -X POST http://localhost:8000/api/v1/tokens \
  -H "Content-Type: application/json" \
  -d '{
    "unidad_id": "UNIT-003",
    "device_id": "GPS-DEVICE-003",
    "ttl_seconds": 2592000,
    "revoke_old": false
  }' | jq -r '.token_plain')

print_success "Tokens generados"

# Guardar tokens
cat > /tmp/tokens.txt << EOF
UNIT-001 (GPS-DEVICE-001): $TOKEN_1
UNIT-002 (GPS-DEVICE-002): $TOKEN_2
UNIT-003 (GPS-DEVICE-003): $TOKEN_3
EOF

chmod 600 /tmp/tokens.txt

echo ""
echo "10. Configurando simulador..."

# Crear device_config.json con tokens
cat > simulator/device_config.json << EOF
{
  "devices": [
    {
      "unidad_id": "UNIT-001",
      "device_id": "GPS-DEVICE-001",
      "token": "$TOKEN_1",
      "token_expires_at": null,
      "last_renewal": null
    },
    {
      "unidad_id": "UNIT-002",
      "device_id": "GPS-DEVICE-002",
      "token": "$TOKEN_2",
      "token_expires_at": null,
      "last_renewal": null
    },
    {
      "unidad_id": "UNIT-003",
      "device_id": "GPS-DEVICE-003",
      "token": "$TOKEN_3",
      "token_expires_at": null,
      "last_renewal": null
    }
  ],
  "server_url": "ws://localhost:8000/ws/device",
  "auto_renewal_enabled": true,
  "renewal_threshold_minutes": 7
}
EOF

print_success "Simulador configurado con tokens en device_config.json"

echo ""
echo "=========================================="
echo "  ✓ Instalación Completada"
echo "=========================================="
echo ""
echo "📊 Información del Sistema:"
echo ""
echo "Backend:"
echo "  - URL: http://localhost:8000"
echo "  - Docs: http://localhost:8000/docs"
echo "  - Estado: systemctl status transporte-backend"
echo ""
echo "Frontend:"
echo "  - Directorio: $(pwd)/frontend"
echo "  - Iniciar: cd frontend && npm run dev"
echo "  - URL: http://localhost:5173"
echo ""
echo "Base de Datos:"
echo "  - Host: localhost:5432"
echo "  - Database: transporte_db"
echo "  - User: app_user"
echo "  - Password: (guardado en /tmp/db_password.txt)"
echo ""
echo "Simulador GPS:"
echo "  - Directorio: $(pwd)/simulator"
echo "  - Configuración: device_config.json (ya configurado con tokens)"
echo "  - Tokens: (guardados en /tmp/tokens.txt)"
echo "  - Ejecutar: cd simulator && python3 gps_simulator_with_renewal.py -i 5"
echo ""
echo "🔐 Archivos de Seguridad (eliminar después de copiar):"
echo "  - /tmp/db_password.txt"
echo "  - /tmp/tokens.txt"
echo ""
echo "📚 Siguientes Pasos:"
echo ""
echo "1. Iniciar frontend:"
echo "   cd frontend && npm run dev"
echo ""
echo "2. Abrir dashboard:"
echo "   http://localhost:5173"
echo ""
echo "3. Iniciar simulador (en otra terminal):"
echo "   cd simulator"
echo "   python3 -m venv venv"
echo "   source venv/bin/activate"
echo "   pip install -r requirements.txt"
echo "   python3 gps_simulator_with_renewal.py -i 5"
echo ""
echo "4. Ver en el dashboard el movimiento de las unidades"
echo ""
echo "=========================================="
