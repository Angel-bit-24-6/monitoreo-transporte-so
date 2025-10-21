# 🚀 Inicio Rápido - Sistema de Monitoreo

**Elige tu sistema operativo:**

---

## 🪟 Estoy en Windows 11/10

### Opción A: Docker Desktop (Más Fácil)

1. **Instalar Docker Desktop**
   - Descargar: https://www.docker.com/products/docker-desktop/
   - Instalar y reiniciar

2. **Iniciar proyecto**
   ```cmd
   docker-compose up -d --build
   ```

3. **Acceder**
   - Backend: http://localhost:8000/docs
   - Frontend: http://localhost:5173

✅ **Listo en 5 minutos**

---

### Opción B: Instalación Nativa (Sin Docker)

1. **Ver guía completa**: [INSTALL_WINDOWS.md](INSTALL_WINDOWS.md)

2. **Resumen rápido:**
   ```cmd
   REM 1. Instalar PostgreSQL + PostGIS
   REM 2. Instalar Python 3.11+
   REM 3. Instalar Node.js 18+

   REM 4. Backend
   cd backend
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   copy .env.example .env
   REM Editar .env con tu password de PostgreSQL

   REM 5. Iniciar
   start_backend.bat
   ```

3. **Frontend (nueva terminal)**
   ```cmd
   start_frontend.bat
   ```

4. **Simulador (nueva terminal)**
   ```cmd
   start_simulator.bat
   ```

---

## 🐧 Estoy en Ubuntu/Linux

### Opción A: Script Automático (Recomendado)

```bash
cd version_web
chmod +x setup.sh
sudo ./setup.sh
```

✅ **Instala TODO automáticamente en 15 minutos**

---

### Opción B: Docker

```bash
# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Iniciar proyecto
docker-compose up -d --build
```

---

### Opción C: Manual

Ver guía completa: [INSTALL_UBUNTU.md](INSTALL_UBUNTU.md)

**Resumen:**
```bash
# 1. Instalar dependencias
sudo apt install postgresql-14 postgresql-14-postgis-3 python3.11 nodejs npm

# 2. Backend
cd backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Editar .env

# 3. Iniciar
./start_backend.sh
./start_frontend.sh
./start_simulator.sh
```

---

## 🔧 Después de Instalar

### 1. Verificar Datos Precargados

**✅ El sistema ya incluye:**
- 3 unidades de prueba: UNIT-001, UNIT-002, UNIT-003
- 1 ruta: **Ruta 1 - Tapachula Centro** (489 puntos GPS)
- Rutas asignadas automáticamente

Verifica en: http://localhost:8000/docs → `GET /api/v1/unidades` y `GET /api/v1/rutas`

### 2. Generar Token

```bash
# Igual en Windows y Linux
curl -X POST http://localhost:8000/api/v1/tokens \
  -H "Content-Type: application/json" \
  -d '{"unidad_id":"UNIT-001","device_id":"GPS-001","ttl_seconds":2592000}'
```

**⚠️ Copiar el token de la respuesta**

### 3. Configurar Simulador

Editar `simulator/device_config.json`:

```json
{
  "server_url": "ws://localhost:8000/ws/device",
  "devices": [
    {
      "unidad_id": "UNIT-001",
      "device_id": "GPS-001",
      "token": "PEGAR_TOKEN_AQUI",
      "token_expires_at": null
    }
  ]
}
```

### 4. Ejecutar Simulador

**Windows:**
```cmd
start_simulator.bat
```

**Linux:**
```bash
./start_simulator.sh
```

**📝 Nota:** Los scripts automáticamente:
- Crean el entorno virtual Python (`venv`) si no existe
- Activan el entorno virtual
- Instalan dependencias si es necesario
- Ejecutan el simulador con renovación automática de tokens

### 5. Abrir Dashboard

http://localhost:5173

**¡Deberías ver las unidades moviéndose en el mapa! 🎉**

---

## 📚 Documentación Completa

- **README principal**: [README.md](README.md)
- **Windows**: [INSTALL_WINDOWS.md](INSTALL_WINDOWS.md)
- **Ubuntu/Linux**: [INSTALL_UBUNTU.md](INSTALL_UBUNTU.md)
- **Deployment**: [DEPLOYMENT.md](DEPLOYMENT.md)
- **API Docs**: http://localhost:8000/docs (después de iniciar)

---

## ❓ Problemas Comunes

### "python no se reconoce como comando" (Windows)

Reinstalar Python marcando "Add Python to PATH"

### "Permission denied" (Linux)

```bash
chmod +x setup.sh
chmod +x start_*.sh
```

### Backend no inicia

**Verificar PostgreSQL:**
- Windows: Servicios → postgresql debe estar corriendo
- Linux: `sudo systemctl status postgresql`

**Verificar .env:**
- Archivo `backend/.env` debe existir
- Password de PostgreSQL debe ser correcto

### Puerto 8000 ya en uso

**Windows:**
```cmd
netstat -ano | findstr :8000
taskkill /F /PID <PID>
```

**Linux:**
```bash
sudo lsof -i :8000
kill -9 <PID>
```

---

## 🎯 Siguientes Pasos

1. ✅ Instalación completa
2. ✅ Datos de prueba creados
3. ✅ Simulador funcionando
4. ✅ Dashboard mostrando posiciones

**Ahora puedes:**
- Crear más unidades y rutas via API
- Modificar umbrales de detección en `.env`
- Ver eventos en tiempo real
- Probar diferentes escenarios con el simulador
- **✨ Probar el chatbot**: Clic en botón 💬 y escribe "Hospitales" o "Farmacias cerca"
- **📍 Ver POIs**: 22 lugares de interés ya están cargados en Tapachula (hospitales, farmacias, bancos, gasolineras, papelerías)

---

## 📞 Ayuda

¿Algo no funciona?

1. Revisar logs del backend
2. Abrir consola del navegador (F12)
3. Verificar que todos los servicios estén corriendo
4. Consultar documentación específica de tu OS

---

**¡Éxito con tu proyecto! 🚀**
