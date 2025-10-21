# Sistema de Autenticación y Tokens
## Monitoreo de Transporte y Seguridad Vial

**Versión:** 3.0 - Configuración via `.env`

---

## 📋 Índice

1. [Introducción](#1-introducción)
2. [Configuración via .env](#2-configuración-via-env)
3. [Cambiar Entre Modos](#3-cambiar-entre-modos)
4. [Renovación Automática](#4-renovación-automática)
5. [Gestión de Tokens via API](#5-gestión-de-tokens-via-api)
6. [Múltiples Dispositivos](#6-múltiples-dispositivos)
7. [Seguridad del Sistema](#7-seguridad-del-sistema)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Introducción

### 🔑 ¿Qué son los Tokens?

Los tokens son credenciales de autenticación que permiten a los dispositivos GPS conectarse al backend de forma segura.

**Características:**
- ✅ **SHA-256 hasheados** - Nunca se almacenan en texto plano
- ✅ **Multi-token** - Múltiples tokens por unidad
- ✅ **Multi-device** - Identificación por `device_id`
- ✅ **TTL configurable** - Expiración personalizable
- ✅ **Renovación automática** - Sin interrupciones de servicio
- ✅ **Grace period** - Token viejo y nuevo coexisten durante transición

### 🔐 Flujo de Autenticación

```
┌─────────────────┐
│ 1. Crear Token  │  POST /api/v1/tokens
│    via API      │  → Devuelve token_plain (solo 1 vez)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 2. Guardar Token│  Dispositivo guarda token en config
│    en Dispositivo│ (device_config.json, .env, etc.)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 3. Conectar WS  │  ws://backend/ws/device
│    y Autenticar │  → Envía AUTH {token, device_id}
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 4. Backend      │  fn_verify_unidad_token()
│    Verifica     │  → Compara hash, expiry, revoked
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 5. AUTH_OK      │  Conexión autenticada
│    o FAILED     │  → Inicia envío de posiciones
└─────────────────┘
```

---

## 2. Configuración via .env

### 📁 Archivos de Configuración

El sistema usa **archivos .env** para configurar el comportamiento de los tokens. Ya no necesitas editar código Python.

| Archivo | Propósito | Cuándo usar |
|---------|-----------|-------------|
| `.env.example` | Template con documentación | Referencia, NO editar |
| `.env.testing` | Preset para testing (10 min) | Desarrollo y pruebas |
| `.env.production` | Preset para producción (30 días) | Despliegue real |
| `.env` | **Archivo activo** (NO en git) | Creado por ti al configurar |

### ⚙️ Variables de Configuración

Ubicación: `backend/.env`

```env
# ==========================================
# CONFIGURACIÓN DE TOKENS
# ==========================================

# Duración del token (en SEGUNDOS)
# Testing:    600 segundos = 10 minutos
# Producción: 2592000 segundos = 30 días
TOKEN_TTL_SECONDS=2592000

# Umbral para renovación automática (en MINUTOS antes de expirar)
# Testing:    7 minutos (renovar cuando falten 7 min)
# Producción: 10080 minutos = 7 días (renovar cuando falten 7 días)
TOKEN_RENEWAL_THRESHOLD_MINUTES=10080

# Intervalo de verificación para renovación (en SEGUNDOS)
# Con qué frecuencia se verifica si un token necesita renovación
# Testing:    60 segundos = 1 minuto
# Producción: 3600 segundos = 1 hora
# IMPACTO: En producción, 3600s reduce queries de 43,200 a 720 por periodo
TOKEN_RENEWAL_CHECK_INTERVAL_SECONDS=3600

# Periodo de gracia (en DÍAS)
# Durante este tiempo, el token viejo y nuevo coexisten
TOKEN_GRACE_PERIOD_DAYS=7

# Limpieza de tokens antiguos (en DÍAS)
# Eliminar tokens revocados/expirados más antiguos que este valor
CLEANUP_TOKEN_DAYS=30
```

### 📊 Tabla Comparativa de Modos

| Parámetro | Testing | Producción | Descripción |
|-----------|---------|------------|-------------|
| **TTL del Token** | 600 seg (10 min) | 2,592,000 seg (30 días) | Cuánto tiempo vive el token |
| **Umbral de Renovación** | 7 min | 10,080 min (7 días) | Cuándo iniciar renovación |
| **Intervalo de Verificación** | 60 seg (1 min) | 3,600 seg (1 hora) | Frecuencia de checks |
| **Renovación Ocurre** | Minuto 3 | Día 23 | Momento real de renovación |
| **Token Expira** | Minuto 10 | Día 30 | Momento de expiración |
| **Grace Period** | Min 3-10 (7 min) | Día 23-30 (7 días) | Ambos tokens válidos |
| **Verificaciones Totales** | 10 checks | 720 checks | Total de queries en periodo |
| **Uso Recomendado** | Desarrollo local | Servidor producción | Entorno de uso |

---

## 3. Cambiar Entre Modos

### ⚡ Cambio Rápido

#### 🧪 Activar Modo Testing (10 minutos)

```bash
cd backend
cp .env.testing .env
# Reiniciar backend
```

**Configuración aplicada:**
- ✅ TTL del token: **10 minutos**
- ✅ Renovación cuando falten: **7 minutos**
- ✅ Verificación cada: **60 segundos**
- ✅ Timeline: Renovación en el minuto 3

**Uso:** Desarrollo, pruebas, depuración de renovación

---

#### 🚀 Activar Modo Producción (30 días)

```bash
cd backend
cp .env.production .env
# Reiniciar backend
```

**Configuración aplicada:**
- ✅ TTL del token: **30 días**
- ✅ Renovación cuando falten: **7 días**
- ✅ Verificación cada: **3600 segundos (1 hora)**
- ✅ Timeline: Renovación en el día 23

**Uso:** Despliegue final, operación real

---

### 📋 Proceso Completo de Cambio

#### Testing → Producción

```bash
# 1. Cambiar configuración
cd backend
cp .env.production .env

# 2. Reiniciar backend
# Windows:
start_backend.bat

# Linux:
./start_backend.sh

# 3. Verificar en logs (al iniciar el backend)
# Deberías ver:
# {
#   "event": "token_configuration_loaded",
#   "mode": "PRODUCCIÓN",
#   "ttl": "30 días",
#   "renewal_threshold": "7 días",
#   "check_interval": "1 horas",
#   "grace_period_days": 7
# }

# 4. Crear nuevos tokens vía Swagger UI
# - Ir a: http://localhost:8000/docs
# - POST /api/v1/tokens
# - Los tokens se crearán con TTL de 30 días automáticamente

# 5. Actualizar simulador
# - Copiar nuevos tokens a simulator/device_config.json
# - Reiniciar simulador
```

---

### ✅ Checklist de Verificación

Después de cambiar de modo:

- [ ] Archivo `.env` actualizado
- [ ] Backend reiniciado
- [ ] Log de configuración verificado (modo correcto)
- [ ] Nuevos tokens creados vía Swagger UI
- [ ] `device_config.json` actualizado con nuevos tokens
- [ ] Simulador reiniciado
- [ ] Renovación automática funcionando

---

### 🔍 Verificar Configuración Actual

#### En el Backend (al iniciar)

Busca en los logs:

```json
{
  "event": "token_configuration_loaded",
  "mode": "TESTING" | "PRODUCCIÓN",
  "ttl": "...",
  "renewal_threshold": "...",
  "check_interval": "...",
  "grace_period_days": 7
}
```

#### En la Base de Datos

```sql
-- Ver tokens activos y su expiración
SELECT
  id,
  unidad_id,
  device_id,
  created_at,
  expires_at,
  expires_at - NOW() AS time_remaining
FROM unidad_token
WHERE revoked = FALSE
ORDER BY created_at DESC;
```

#### En los Logs del Simulador

Cada intervalo de verificación deberías ver:

```json
{
  "event": "token_renewal_check",
  "unidad_id": "UNIT-001",
  "minutes_until_expiry": 8.5,
  "threshold_minutes": 7,
  "should_renew": false
}
```

Cuando llegue el momento:

```json
{
  "event": "token_renewal_check",
  "should_renew": true
}
{
  "event": "initiating_token_renewal"
}
{
  "event": "token_renewal_sent",
  "new_token_id": 42
}
```

---

## 4. Renovación Automática

### 🔄 Ciclo de Vida del Token

```
┌─────────────┐
│Token Creado │  TTL: 10 min (testing) / 30 días (producción)
└──────┬──────┘
       │
       ▼
┌────────────────────────┐
│ Dispositivo Operando   │  Conexión WebSocket autenticada
│ Token Válido           │  Envío de posiciones GPS
└──────┬─────────────────┘
       │
       ▼ (Testing: min 3 | Producción: día 23)
┌────────────────────────┐
│ Backend Detecta        │  should_renew_token() = TRUE
│ Necesidad de Renovar   │  (faltan <= umbral minutos)
└──────┬─────────────────┘
       │
       ▼
┌────────────────────────┐
│ Backend Crea Nuevo     │  fn_create_unidad_token_for_device()
│ Token (NO revoca old)  │  revoke_old = FALSE
└──────┬─────────────────┘
       │
       ▼
┌────────────────────────┐
│ Envío WebSocket        │  Mensaje: TOKEN_RENEWAL
│ TOKEN_RENEWAL          │  {new_token, expires_at, grace_period}
└──────┬─────────────────┘
       │
       ▼
┌────────────────────────┐
│ Dispositivo Recibe     │  handle_token_renewal()
│ Guarda Nuevo Token     │  update_device_token()
└──────┬─────────────────┘
       │
       ▼
┌────────────────────────┐
│ Confirmación ACK       │  TOKEN_RENEWAL_ACK
│ new_token_saved=true   │  {message: "Token guardado"}
└──────┬─────────────────┘
       │
       ▼
┌────────────────────────┐
│ Grace Period Activo    │  Token viejo y nuevo válidos
│ (7 días)               │  Tiempo para actualizar config
└──────┬─────────────────┘
       │
       ▼
┌────────────────────────┐
│ Token Viejo Expira     │  Solo token nuevo válido
│ Fin de Grace Period    │  Conexión continua sin interrupciones
└────────────────────────┘
```

### ⏱️ Timeline de Renovación

#### Modo Testing (10 minutos)

```
Minuto 0:  ✅ Token creado (expira en minuto 10)
           ✅ Dispositivo se conecta
           ✅ Tarea de verificación inicia (cada 60s)

Minuto 1:  🔍 Verificación: faltan 9 min → NO renovar
Minuto 2:  🔍 Verificación: faltan 8 min → NO renovar
Minuto 3:  🔄 Verificación: faltan 7 min → RENOVAR ✅
           ✅ Nuevo token creado
           ✅ Mensaje TOKEN_RENEWAL enviado
           ✅ Dispositivo guarda nuevo token
           ✅ ACK recibido
           ⚠️  Token viejo sigue válido (grace period)

Minuto 4-9: 🔍 Verificaciones continuas (ambos tokens válidos)

Minuto 10: ❌ Token original expira
           ✅ Solo token nuevo válido
           ✅ Conexión continúa sin interrupciones

Minuto 13: 🔄 Renovación automática del nuevo token
           (repite el ciclo cada 10 minutos)
```

#### Modo Producción (30 días)

```
Día 0:  ✅ Token creado (expira en día 30)
        ✅ Dispositivo se conecta
        ✅ Tarea de verificación inicia (cada 1 hora)

Día 1-22: 🔍 Verificaciones cada hora: faltan > 7 días → NO renovar
          (Total: ~528 verificaciones)

Día 23: 🔄 Verificación: faltan 7 días → RENOVAR ✅
        ✅ Nuevo token creado
        ✅ Mensaje TOKEN_RENEWAL enviado
        ✅ Dispositivo guarda nuevo token
        ✅ ACK recibido
        ⚠️  Token viejo sigue válido (grace period 7 días)

Día 24-29: 🔍 Verificaciones continuas cada hora
           (Ambos tokens válidos)

Día 30: ❌ Token original expira
        ✅ Solo token nuevo válido
        ✅ Conexión continúa sin interrupciones

Día 53: 🔄 Renovación automática del nuevo token
        (repite el ciclo cada 30 días)
```

### 🔧 Componentes del Sistema

#### Backend: Verificación Periódica

**Archivo:** `backend/app/websockets/device_handler.py`

```python
async def _token_renewal_checker(self):
    """
    Tarea periódica para verificar si el token necesita renovación.
    """
    while self.running:
        try:
            # Verificar si necesita renovación (lee configuración desde .env)
            should_renew = await AuthService.should_renew_token(
                self.unidad_id,
                self.device_id
            )

            if should_renew:
                await self._send_token_renewal()

            # Esperar intervalo configurable (60s testing / 3600s producción)
            await asyncio.sleep(settings.TOKEN_RENEWAL_CHECK_INTERVAL_SECONDS)

        except asyncio.CancelledError:
            break
```

#### Backend: Creación de Nuevo Token

```python
async def _send_token_renewal(self):
    """
    Crear nuevo token y enviarlo al dispositivo.
    NO revoca el token antiguo (grace period).
    """
    # Crear nuevo token sin revocar el antiguo
    new_token_data = await AuthService.create_token(
        self.unidad_id,
        self.device_id,
        ttl_seconds=settings.TOKEN_TTL_SECONDS,  # Lee desde .env
        revoke_old=False  # IMPORTANTE: No revocar para permitir grace period
    )

    # Preparar mensaje de renovación
    renewal_msg = TokenRenewalResponse(
        new_token=token_plain,
        expires_at=expires_at,
        grace_period_days=settings.TOKEN_GRACE_PERIOD_DAYS,  # Lee desde .env
        message="Token renovado. Actualice su configuración."
    )

    # Enviar al dispositivo
    await self.websocket.send_json(renewal_msg.model_dump())
```

#### Dispositivo: Manejo de Renovación

**Archivo:** `simulator/gps_simulator_with_renewal.py` (implementación actual)

```python
async def handle_token_renewal(self, message):
    """
    Manejar mensaje de renovación de token.
    """
    new_token = message["new_token"]
    expires_at = message["expires_at"]
    grace_period = message["grace_period_days"]

    # Guardar nuevo token en configuración
    self.update_device_token(new_token)

    # Enviar confirmación al backend
    ack_msg = {
        "type": "TOKEN_RENEWAL_ACK",
        "new_token_saved": True,
        "message": "Token guardado exitosamente"
    }
    await self.websocket.send(json.dumps(ack_msg))

    logger.info(
        "token_renewed_successfully",
        expires_at=expires_at,
        grace_period_days=grace_period
    )
```

---

## 5. Gestión de Tokens via API

### 🔑 Crear Token

**Endpoint:** `POST /api/v1/tokens`

**Windows (PowerShell/CMD):**
```cmd
curl -X POST http://localhost:8000/api/v1/tokens ^
  -H "Content-Type: application/json" ^
  -d "{\"unidad_id\":\"UNIT-001\",\"device_id\":\"GPS-001\",\"ttl_seconds\":2592000,\"revoke_old\":false}"
```

**Linux:**
```bash
curl -X POST http://localhost:8000/api/v1/tokens \
  -H "Content-Type: application/json" \
  -d '{"unidad_id":"UNIT-001","device_id":"GPS-001","ttl_seconds":2592000,"revoke_old":false}'
```

**Respuesta:**
```json
{
  "token_plain": "abc123def456ghi789...",
  "token_id": 1,
  "unidad_id": "UNIT-001",
  "device_id": "GPS-001",
  "expires_at": "2025-11-13T10:30:00Z",
  "message": "Token creado exitosamente. Guárdelo de forma segura, no se mostrará nuevamente."
}
```

⚠️ **IMPORTANTE:**
- El `token_plain` solo se muestra **UNA VEZ**
- Cópialo inmediatamente
- Nunca se podrá recuperar después

### 🔄 Parámetros de Creación

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `unidad_id` | string | ✅ | ID de la unidad (ej: "UNIT-001") |
| `device_id` | string | ✅ | ID del dispositivo GPS |
| `ttl_seconds` | int | ❌ | Duración del token. Si no se especifica, usa `TOKEN_TTL_SECONDS` del .env |
| `revoke_old` | bool | ❌ | Si `true`, revoca tokens anteriores del mismo device_id. Default: `false` |

### ❌ Revocar Token Específico

**Endpoint:** `DELETE /api/v1/tokens/revoke`

```bash
curl -X DELETE http://localhost:8000/api/v1/tokens/revoke \
  -H "Content-Type: application/json" \
  -d '{"token_plain":"abc123def456..."}'
```

### ❌ Revocar Todos los Tokens de un Dispositivo

**Endpoint:** `DELETE /api/v1/tokens/device/{unidad_id}/{device_id}`

```bash
curl -X DELETE http://localhost:8000/api/v1/tokens/device/UNIT-001/GPS-001
```

**Respuesta:**
```json
{
  "revoked_count": 3,
  "message": "3 tokens revocados para UNIT-001 / GPS-001"
}
```

---

## 6. Múltiples Dispositivos

### 🚗 Renovación Independiente

**IMPORTANTE:** La renovación automática funciona **independientemente para cada unidad**.

Cuando tienes 3 unidades conectadas (UNIT-001, UNIT-002, UNIT-003):
- Cada una tiene su propio WebSocket connection al backend
- Cada conexión tiene su propio task `_token_renewal_checker()` corriendo cada 60s (testing) / 3600s (producción)
- Cada unidad renueva su token **independientemente** según su propia fecha de expiración

### 📊 Escenarios de Renovación

#### Escenario A: Tokens creados simultáneamente

```
Todos expiran en 10 minutos:

Minuto 0:   UNIT-001, UNIT-002, UNIT-003 se conectan
Minuto 3:   ✅ UNIT-001 renueva
            ✅ UNIT-002 renueva  (casi simultáneamente)
            ✅ UNIT-003 renueva
Minuto 10:  Los 3 tokens originales expiran
Minuto 13:  ✅ UNIT-001 renueva nuevamente
            ✅ UNIT-002 renueva nuevamente
            ✅ UNIT-003 renueva nuevamente
```

#### Escenario B: Tokens creados en diferentes momentos

```
Expiraciones escalonadas:

Minuto 0:   UNIT-001 se conecta (token expira min 10)
Minuto 2:   UNIT-002 se conecta (token expira min 12)
Minuto 5:   UNIT-003 se conecta (token expira min 15)

Minuto 3:   ✅ UNIT-001 renueva (solo esta unidad)
Minuto 5:   ✅ UNIT-002 renueva (solo esta unidad)
Minuto 8:   ✅ UNIT-003 renueva (solo esta unidad)
```

### 🏭 Escalabilidad

El sistema soporta **cientos de unidades** renovando automáticamente:

```
100 unidades en producción:
- 100 conexiones WebSocket activas
- 100 tareas de verificación (cada 1 hora)
- Renovación distribuida a lo largo del mes
- Sin overhead significativo en la BD
```

**Impacto en BD:**
- Testing (60s interval): 100 unidades × 10 queries/10min = 1,000 queries cada 10 min
- Producción (3600s interval): 100 unidades × 720 queries/30días = 72,000 queries cada 30 días
- Con índices apropiados: < 1ms por query

---

## 7. Seguridad del Sistema

### 🔐 Almacenamiento Seguro

#### En Base de Datos

```sql
-- Tokens NUNCA se guardan en texto plano
CREATE TABLE unidad_token (
    id SERIAL PRIMARY KEY,
    unidad_id TEXT NOT NULL,
    device_id TEXT NOT NULL,
    token_hash BYTEA NOT NULL,  -- ← SHA-256 hash (32 bytes)
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    last_used TIMESTAMPTZ,
    revoked BOOLEAN DEFAULT FALSE
);
```

**Proceso de hashing:**
```sql
-- Al crear token
token_hash = digest(token_plain, 'sha256')

-- Al verificar token
SELECT * FROM unidad_token
WHERE token_hash = digest($1, 'sha256')
  AND revoked = FALSE
  AND (expires_at IS NULL OR expires_at > now());
```

#### En Tránsito

- ✅ **WebSocket sobre TLS** en producción (`wss://`)
- ✅ **HTTPS** para API REST
- ✅ Token solo viaja en texto plano durante:
  1. Creación inicial (respuesta API)
  2. Mensaje de renovación (WebSocket)
  3. Autenticación inicial (WebSocket)

### 🛡️ Protecciones Implementadas

1. **Expiración Automática**
   - Tokens no permanentes (excepto si TTL = 0)
   - Grace period limitado (7 días)

2. **Revocación Inmediata**
   - Via API: `DELETE /api/v1/tokens/revoke`
   - Via SQL: `UPDATE unidad_token SET revoked = TRUE WHERE ...`

3. **Multi-device Support**
   - Un dispositivo comprometido no afecta otros dispositivos de la misma unidad
   - Revocación granular por `device_id`

4. **Auditoría**
   - Campo `last_used` actualizado en cada verificación
   - Logs estructurados de todas las operaciones
   - Timestamp de creación y expiración

5. **Cleanup Automático**
   - Función `fn_cleanup_expired_tokens()` elimina tokens antiguos
   - Configurable via `CLEANUP_TOKEN_DAYS` (default: 30 días)

### ⚠️ Consideraciones de Seguridad

#### ¿Qué pasa si roban un token?

**Escenario:** Atacante obtiene un token válido.

**Opciones de mitigación:**

1. **Revocar token inmediatamente:**
   ```bash
   curl -X DELETE http://localhost:8000/api/v1/tokens/revoke \
     -H "Content-Type: application/json" \
     -d '{"token_plain":"TOKEN_ROBADO"}'
   ```

2. **Revocar todos los tokens del dispositivo:**
   ```bash
   curl -X DELETE http://localhost:8000/api/v1/tokens/device/UNIT-001/GPS-001
   ```

3. **Crear nuevo token y actualizar dispositivo legítimo:**
   ```bash
   # Revocar viejo
   curl -X POST http://localhost:8000/api/v1/tokens \
     -d '{"unidad_id":"UNIT-001","device_id":"GPS-001","revoke_old":true}'
   ```

#### ¿Un atacante puede desplazar al dispositivo legítimo?

**Actual:** Sí, última conexión gana.

```python
# connection_manager.py
connection_manager.device_connections[self.device_id] = connection
```

**Mejora recomendada (futuro):**
```python
# Rechazar nuevas conexiones si ya existe una activa
if self.device_id in connection_manager.device_connections:
    existing_conn = connection_manager.device_connections[self.device_id]
    if existing_conn.is_active():
        logger.warning("duplicate_connection_attempt", device_id=self.device_id)
        await self.websocket.close(code=4002, reason="Device already connected")
        return
```

---

## 8. Troubleshooting

### ❌ Token no se acepta al conectar

**Síntomas:**
```json
{
  "type": "AUTH_FAILED",
  "reason": "Token inválido o expirado"
}
```

**Causas posibles:**

1. **Token expirado**
   ```sql
   -- Verificar en BD
   SELECT unidad_id, device_id, expires_at, expires_at < now() as expired
   FROM unidad_token
   WHERE token_hash = digest('TU_TOKEN', 'sha256');
   ```

   **Solución:** Crear nuevo token.

2. **Token revocado**
   ```sql
   SELECT unidad_id, device_id, revoked
   FROM unidad_token
   WHERE token_hash = digest('TU_TOKEN', 'sha256');
   ```

   **Solución:** Crear nuevo token.

3. **Token incorrecto**
   - Verificar que copiaste el token completo
   - Sin espacios al inicio/final
   - Case-sensitive

4. **Token de otra unidad**
   ```bash
   # Token de UNIT-002 no funciona para UNIT-001
   ```

   **Solución:** Usar token correcto para la unidad.

---

### ⏰ Renovación no ocurre

**Síntomas:**
- No aparece log `initiating_token_renewal`
- Token expira sin renovación previa

**Diagnóstico:**

1. **Verificar configuración .env:**
   ```bash
   cat backend/.env | grep TOKEN_
   ```

   Debe mostrar:
   ```env
   TOKEN_TTL_SECONDS=600
   TOKEN_RENEWAL_THRESHOLD_MINUTES=7
   TOKEN_RENEWAL_CHECK_INTERVAL_SECONDS=60
   ```

2. **Verificar logs de configuración al iniciar backend:**
   ```json
   {
     "event": "token_configuration_loaded",
     "mode": "TESTING",
     "ttl": "10 minutos",
     "renewal_threshold": "7 minutos",
     "check_interval": "1 minutos"
   }
   ```

3. **Verificar logs de verificación cada 60s:**
   ```json
   {
     "event": "token_renewal_check",
     "unidad_id": "UNIT-001",
     "minutes_until_expiry": 8.5,
     "threshold_minutes": 7,
     "should_renew": false
   }
   ```

4. **Verificar que el backend se reinició después de cambiar .env:**
   - Backend NO recarga .env automáticamente
   - Ctrl+C y volver a ejecutar `start_backend.bat` o `./start_backend.sh`

---

### 🔄 Modo no cambia

**Síntoma:**
- Logs siguen mostrando modo antiguo después de `cp .env.production .env`

**Causa:**
- Backend no recarga `.env` en caliente

**Solución:**
```bash
# 1. Detener backend (Ctrl+C)
# 2. Verificar que .env cambió
cat backend/.env | head -30

# 3. Reiniciar backend
cd backend
./start_backend.sh  # Linux
start_backend.bat   # Windows

# 4. Verificar logs de inicio
# Debe mostrar modo correcto
```

---

### 🗄️ Tokens creados con TTL incorrecto

**Síntoma:**
- Creé token en modo producción pero expira en 10 minutos

**Causa:**
- Los tokens se crean con la configuración de `.env` AL MOMENTO de crearlos
- Si cambias `.env` después, los tokens viejos siguen con su TTL original

**Solución:**
```bash
# 1. Cambiar .env
cp .env.production .env

# 2. Reiniciar backend
./start_backend.sh

# 3. Crear NUEVOS tokens (los viejos no se modifican)
curl -X POST http://localhost:8000/api/v1/tokens \
  -d '{"unidad_id":"UNIT-001","device_id":"GPS-001"}'

# 4. Actualizar dispositivo con nuevo token
# Editar device_config.json o simulator config
```

---

### 📊 Verificaciones demasiado frecuentes

**Síntoma:**
- Logs llenos de `token_renewal_check` cada minuto en producción

**Causa:**
- `TOKEN_RENEWAL_CHECK_INTERVAL_SECONDS` configurado para testing (60s)

**Solución:**
```bash
# 1. Verificar .env
cat backend/.env | grep TOKEN_RENEWAL_CHECK_INTERVAL_SECONDS
# Debe ser 3600 para producción

# 2. Si está en 60, usar preset correcto
cp .env.production .env

# 3. Reiniciar backend
./start_backend.sh
```

---

## 📚 Referencias

### Archivos Relacionados

- **Configuración:** `backend/.env`, `.env.example`, `.env.testing`, `.env.production`
- **Backend:**
  - `backend/app/core/config.py` - Carga configuración
  - `backend/app/services/auth_service.py` - Lógica de autenticación
  - `backend/app/websockets/device_handler.py` - Renovación automática
  - `backend/app/api/tokens.py` - API REST de tokens
- **Database:** `migrations/migrations_full_final_with_device_FIXED.sql` - Funciones PL/pgSQL
- **Simulador:** `simulator/gps_simulator_with_renewal.py` - Implementación cliente con renovación automática

### Documentación Adicional

- [README.md](../README.md) - Documentación principal
- [ARQUITECTURA.md](ARQUITECTURA.md) - Diseño del sistema
- [QUICK_START.md](../QUICK_START.md) - Inicio rápido

---

**Versión:** 3.0
**Última actualización:** Octubre 2025
**Autor:** Sistema de Monitoreo UNACH
