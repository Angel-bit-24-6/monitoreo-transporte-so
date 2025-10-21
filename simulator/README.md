# Simulador GPS con Renovación Automática de Tokens

Simulador de dispositivos GPS que se conecta al backend via WebSocket y envía posiciones periódicas.

## 🔧 Configuración

### 1. Crear archivo de configuración

```bash
# Copiar el archivo de ejemplo
cp device_config.json.example device_config.json
```

### 2. Generar tokens

Usa la API del backend para generar tokens para cada dispositivo:

```bash
curl -X POST http://localhost:8000/api/v1/tokens \
  -H "Content-Type: application/json" \
  -d '{
    "unidad_id": "UNIT-001",
    "device_id": "GPS-DEVICE-001",
    "ttl_seconds": 2592000,
    "revoke_old": false
  }'
```

Copia el `token_plain` de la respuesta.

### 3. Editar device_config.json

```json
{
  "devices": [
    {
      "unidad_id": "UNIT-001",
      "device_id": "GPS-DEVICE-001",
      "token": "PEGAR_TOKEN_AQUI",
      "token_expires_at": null,
      "last_renewal": null
    }
  ],
  "server_url": "ws://localhost:8000/ws/device",
  "auto_renewal_enabled": true,
  "renewal_threshold_minutes": 7
}
```

## 🚀 Ejecución

### Opción 1: Scripts automáticos (Recomendado)

**Windows:**
```cmd
..\start_simulator.bat
```

**Linux:**
```bash
../start_simulator.sh
```

Los scripts automáticamente:
- Crean el entorno virtual si no existe
- Instalan dependencias
- Ejecutan el simulador

### Opción 2: Manual

```bash
# Crear entorno virtual
python -m venv venv

# Activar
# Windows:
venv\Scripts\activate
# Linux:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar
python gps_simulator_with_renewal.py -i 5
```

## 📝 Opciones de línea de comandos

```bash
python gps_simulator_with_renewal.py --help

Opciones:
  -i, --interval SECONDS    Intervalo de envío de posiciones (default: 5)
  -h, --help               Mostrar ayuda
```

## 🔄 Renovación Automática de Tokens

El simulador renueva automáticamente los tokens antes de que expiren:

- **Testing:** Renueva cuando faltan 7 minutos (tokens de 10 min)
- **Producción:** Renueva cuando faltan 7 días (tokens de 30 días)

El nuevo token se guarda automáticamente en `device_config.json`.

## ⚠️ IMPORTANTE

- Los tokens se muestran UNA sola vez al crearlos
- Guarda los tokens de forma segura

## 📚 Documentación

Ver [docs/TOKEN_SYSTEM.md](../docs/TOKEN_SYSTEM.md) para más información sobre el sistema de tokens.
