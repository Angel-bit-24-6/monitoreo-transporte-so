# Guía de Despliegue - Sistema de Monitoreo de Transporte

Esta guía cubre el proceso completo de despliegue del sistema desde cero.

---

## 🎯 Opciones de Despliegue

1. **Desarrollo Local** - Para testing y desarrollo
2. **Docker Compose** - Para staging y demo
3. **Producción** - Para deployment real

---

## 1️⃣ Despliegue Local (Desarrollo)

### Paso 1: Preparar PostgreSQL

```bash
# Instalar PostgreSQL + PostGIS (Ubuntu/Debian)
sudo apt update
sudo apt install postgresql postgresql-contrib postgis

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

### Paso 2: Aplicar Migraciones

```bash
cd version_web

# Aplicar schema completo
psql -U postgres -d transporte_db -f migrations/migrations_full_final_with_device_FIXED.sql

# Verificar
psql -U postgres -d transporte_db -c "\dt"
```

### Paso 3: Configurar Backend

```bash
cd backend

# Crear entorno virtual
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate    # Windows

# Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env

# Editar .env
nano .env
# Modificar:
# DATABASE_URL=postgresql://app_user:tu_password@localhost:5432/transporte_db
# DB_USER=app_user
# DB_PASSWORD=tu_password
```

### Paso 4: Iniciar Backend

```bash
# Desarrollo con reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Producción (con workers)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Verificar: http://localhost:8000/docs

### Paso 5: Configurar Frontend

```bash
cd ../frontend

# Instalar Node.js (si no está instalado)
# https://nodejs.org/

# Instalar dependencias
npm install

# Desarrollo
npm run dev

# Build para producción
npm run build
npm run preview
```

Verificar: http://localhost:5173

---

## 2️⃣ Despliegue con Docker Compose

### Prerrequisitos

```bash
# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Instalar Docker Compose
sudo apt install docker-compose-plugin
```

### Paso 1: Configurar Variables

El `docker-compose.yml` está configurado para usar credenciales específicas para la base de datos. Crearemos un archivo `backend/.env` que las refleje.

**Importante:** El `docker-compose.yml` sobreescribirá `DB_HOST` y `DATABASE_URL` para que apunten al contenedor de la base de datos. Sin embargo, las variables `DB_USER` y `DB_PASSWORD` de este archivo **deben** coincidir con las del servicio `postgres` en `docker-compose.yml`.

```bash
cd version_web

# Crear archivo .env para Docker
cat > backend/.env << EOF
# Credenciales que coinciden con el servicio 'postgres' en docker-compose.yml
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=transporte_db

# Variables para el servidor FastAPI
HOST=0.0.0.0
PORT=8000
DEBUG=False
LOG_LEVEL=INFO

# --- El resto de variables de la aplicación serán leídas desde aquí ---
# (Se pueden copiar desde .env.example o .env.production si es necesario)
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
TOKEN_TTL_SECONDS=2592000
TOKEN_RENEWAL_THRESHOLD_MINUTES=10080
TOKEN_RENEWAL_CHECK_INTERVAL_SECONDS=3600
TOKEN_GRACE_PERIOD_DAYS=7
CLEANUP_TOKEN_DAYS=30
WS_HEARTBEAT_INTERVAL=30
WS_TIMEOUT=300
OUT_OF_ROUTE_THRESHOLD_M=200
STOP_SPEED_THRESHOLD=1.5
STOP_TIME_THRESHOLD_S=120
EOF
```

### Paso 2: Iniciar Servicios

```bash
# Build y start
docker-compose up -d --build

# Ver logs
docker-compose logs -f

# Verificar estado
docker-compose ps
```

### Paso 3: Aplicar Migraciones

```bash
# Esperar a que PostgreSQL esté listo
sleep 10

# Aplicar migraciones
docker-compose exec postgres psql -U postgres -d transporte_db -f /docker-entrypoint-initdb.d/migrations_full_final_with_device_FIXED.sql
```

### Paso 4: Verificar Servicios

```bash
# Backend
curl http://localhost:8000/api/v1/health

# Frontend
curl http://localhost:5173
```

### Paso 5: Crear Datos Iniciales

```bash
# Script de inicialización
curl -X POST http://localhost:8000/api/v1/unidades \
  -H "Content-Type: application/json" \
  -d '{
    "id": "UNIT-001",
    "placa": "ABC-123",
    "chofer": "Juan Pérez",
    "activo": true
  }'

# Crear ruta
curl -X POST http://localhost:8000/api/v1/rutas \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Ruta Principal",
    "descripcion": "Centro ciudad",
    "coordinates": [
      [-78.6505, -1.6702],
      [-78.6495, -1.6712],
      [-78.6485, -1.6722],
      [-78.6475, -1.6732]
    ]
  }'

# Asignar ruta
curl -X POST http://localhost:8000/api/v1/rutas/assignments \
  -H "Content-Type: application/json" \
  -d '{
    "unidad_id": "UNIT-001",
    "ruta_id": 1,
    "start_ts": "2025-10-14T00:00:00Z"
  }'

# Crear token
curl -X POST http://localhost:8000/api/v1/tokens \
  -H "Content-Type: application/json" \
  -d '{
    "unidad_id": "UNIT-001",
    "device_id": "GPS-SIM-001",
    "ttl_seconds": 2592000,
    "revoke_old": false
  }'
```

**⚠️ Guardar el token retornado para configurar el simulador**

---

## 3️⃣ Despliegue en Producción

### Arquitectura Recomendada

```
Internet
    |
    v
[Load Balancer / Nginx]
    |
    +---> [Backend FastAPI x4 workers] ---> [PostgreSQL + PostGIS]
    |
    +---> [Frontend Static Files]
```

### Paso 1: Servidor

**Specs Recomendadas:**
- CPU: 4 cores
- RAM: 8GB
- Disco: 50GB SSD
- OS: Ubuntu 22.04 LTS

### Paso 2: Instalar Dependencias

```bash
# System packages
sudo apt update && sudo apt upgrade -y
sudo apt install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    postgresql-14 \
    postgresql-14-postgis-3 \
    nginx \
    certbot \
    python3-certbot-nginx \
    supervisor

# Docker (opcional)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
```

### Paso 3: Configurar PostgreSQL

```bash
# Editar postgresql.conf
sudo nano /etc/postgresql/14/main/postgresql.conf

# Ajustar:
# max_connections = 200
# shared_buffers = 2GB
# effective_cache_size = 6GB
# work_mem = 16MB

# Restart
sudo systemctl restart postgresql

# Crear usuario y base de datos
sudo -u postgres psql << EOF
CREATE USER app_user WITH PASSWORD 'SECURE_PASSWORD_HERE';
CREATE DATABASE transporte_db OWNER app_user;
\c transporte_db
CREATE EXTENSION postgis;
CREATE EXTENSION pgcrypto;
GRANT ALL PRIVILEGES ON DATABASE transporte_db TO app_user;
\q
EOF

# Aplicar migraciones
psql -U app_user -d transporte_db -f migrations/migrations_full_final_with_device_FIXED.sql
```

### Paso 4: Desplegar Backend

```bash
# Crear usuario del sistema
sudo useradd -m -s /bin/bash appuser

# Copiar código
sudo mkdir -p /opt/transporte
sudo cp -r version_web/* /opt/transporte/
sudo chown -R appuser:appuser /opt/transporte

# Setup entorno virtual
sudo -u appuser bash << 'EOF'
cd /opt/transporte/backend
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
EOF

# Configurar .env
sudo nano /opt/transporte/backend/.env
# Modificar con valores de producción
```

### Paso 5: Configurar Supervisor (Backend)

```bash
sudo nano /etc/supervisor/conf.d/transporte-backend.conf
```

```ini
[program:transporte-backend]
command=/opt/transporte/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
directory=/opt/transporte/backend
user=appuser
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
stderr_logfile=/var/log/transporte/backend.err.log
stdout_logfile=/var/log/transporte/backend.out.log
environment=PYTHONUNBUFFERED=1
```

```bash
# Crear directorio de logs
sudo mkdir -p /var/log/transporte
sudo chown appuser:appuser /var/log/transporte

# Recargar supervisor
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start transporte-backend
sudo supervisorctl status
```

### Paso 6: Desplegar Frontend

```bash
cd /opt/transporte/frontend

# Build
npm install
npm run build

# Los archivos están en dist/
# Copiar a directorio de Nginx
sudo cp -r dist/* /var/www/html/transporte/
sudo chown -R www-data:www-data /var/www/html/transporte
```

### Paso 7: Configurar Nginx

```bash
sudo nano /etc/nginx/sites-available/transporte
```

```nginx
upstream backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name tu-dominio.com;

    # Frontend
    location / {
        root /var/www/html/transporte;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # API REST
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket
    location /ws/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 86400;
    }

    # Docs
    location /docs {
        proxy_pass http://backend;
    }

    location /redoc {
        proxy_pass http://backend;
    }
}
```

```bash
# Habilitar sitio
sudo ln -s /etc/nginx/sites-available/transporte /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Paso 8: SSL con Let's Encrypt

```bash
sudo certbot --nginx -d tu-dominio.com

# Auto-renovación (ya configurado)
sudo systemctl status certbot.timer
```

### Paso 9: Firewall

```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

---

## 🔧 Mantenimiento

### Logs

```bash
# Backend
sudo tail -f /var/log/transporte/backend.out.log

# Nginx
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# PostgreSQL
sudo tail -f /var/log/postgresql/postgresql-14-main.log
```

### Backup Base de Datos

```bash
# Backup completo
pg_dump -U app_user -d transporte_db -F c -f backup_$(date +%Y%m%d).dump

# Backup solo schema
pg_dump -U app_user -d transporte_db --schema-only > schema_backup.sql

# Restaurar
pg_restore -U app_user -d transporte_db_new backup_20251014.dump
```

### Actualizar Código

```bash
cd /opt/transporte
sudo git pull origin main

# Backend
sudo supervisorctl restart transporte-backend

# Frontend
cd frontend
npm run build
sudo cp -r dist/* /var/www/html/transporte/
```

### Cleanup Tokens Expirados

```bash
# Crear cron job
sudo crontab -e -u appuser

# Ejecutar diariamente a las 3am
0 3 * * * psql -U app_user -d transporte_db -c "SELECT fn_cleanup_expired_tokens(30);"
```

---

## 📊 Monitoreo

### Métricas PostgreSQL

```sql
-- Conexiones activas
SELECT count(*) FROM pg_stat_activity WHERE state = 'active';

-- Tamaño de tablas
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Eventos últimas 24h
SELECT tipo, COUNT(*)
FROM evento
WHERE ts >= now() - interval '24 hours'
GROUP BY tipo;
```

### Estado del Sistema

```bash
# Procesos
ps aux | grep uvicorn

# Recursos
htop

# Conexiones
netstat -tuln | grep 8000

# WebSockets activos
curl http://localhost:8000/api/v1/status | jq '.websockets'
```

---

## ⚠️ Solución de Problemas

### Backend no inicia

```bash
# Verificar logs
sudo supervisorctl tail -f transporte-backend

# Verificar permisos
ls -la /opt/transporte/backend

# Test manual
cd /opt/transporte/backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Error de conexión a DB

```bash
# Verificar PostgreSQL
sudo systemctl status postgresql

# Test conexión
psql -U app_user -d transporte_db -c "SELECT 1;"

# Ver conexiones
sudo -u postgres psql -c "SELECT * FROM pg_stat_activity;"
```

### WebSocket no conecta

```bash
# Verificar Nginx config
sudo nginx -t

# Ver logs
sudo tail -f /var/log/nginx/error.log

# Test directo (bypass Nginx)
wscat -c ws://localhost:8000/ws/dashboard
```

---

## 🚀 Optimizaciones de Producción

### 1. Indexes Adicionales

```sql
-- Índices para queries frecuentes
CREATE INDEX CONCURRENTLY idx_posicion_ts_unidad ON posicion(ts DESC, unidad_id);
CREATE INDEX CONCURRENTLY idx_evento_ts_tipo ON evento(ts DESC, tipo);
```

### 2. Particionamiento Automático

```sql
-- Función para crear particiones automáticamente
CREATE OR REPLACE FUNCTION create_monthly_partitions()
RETURNS void AS $$
DECLARE
    start_date DATE;
    end_date DATE;
    table_name TEXT;
BEGIN
    FOR i IN 0..2 LOOP
        start_date := date_trunc('month', CURRENT_DATE + (i || ' months')::interval);
        end_date := start_date + interval '1 month';
        table_name := 'posicion_' || to_char(start_date, 'YYYY_MM');

        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I PARTITION OF posicion FOR VALUES FROM (%L) TO (%L)',
            table_name, start_date, end_date
        );

        EXECUTE format(
            'CREATE INDEX IF NOT EXISTS %I ON %I USING GIST (geom)',
            'idx_' || table_name || '_geom', table_name
        );
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Job mensual (cron)
SELECT create_monthly_partitions();
```

### 3. Connection Pooling (PgBouncer)

```bash
sudo apt install pgbouncer

sudo nano /etc/pgbouncer/pgbouncer.ini
```

```ini
[databases]
transporte_db = host=127.0.0.1 port=5432 dbname=transporte_db

[pgbouncer]
listen_addr = 127.0.0.1
listen_port = 6432
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt
pool_mode = transaction
max_client_conn = 200
default_pool_size = 50
```

Modificar backend `.env`:
```
DATABASE_URL=postgresql://app_user:password@localhost:6432/transporte_db
```

---

## ✅ Checklist de Producción

- [ ] PostgreSQL configurado y optimizado
- [ ] Migraciones aplicadas correctamente
- [ ] Backend corriendo con Supervisor
- [ ] Frontend buildead y servido por Nginx
- [ ] SSL/TLS configurado (Let's Encrypt)
- [ ] Firewall configurado
- [ ] Backups automáticos configurados
- [ ] Cleanup de tokens en cron
- [ ] Logs rotando correctamente
- [ ] Monitoreo básico funcionando
- [ ] Documentación actualizada
- [ ] Credenciales seguras (no defaults)

---

## 📞 Contacto y Soporte

Para problemas de deployment, crear issue en GitHub con:
- Logs completos
- Configuración (sin credenciales)
- Pasos para reproducir
- OS y versiones

---

**Última actualización:** Octubre 2025
