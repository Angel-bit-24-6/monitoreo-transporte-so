"""
Aplicación principal FastAPI.
Sistema de Monitoreo de Transporte y Seguridad Vial.
"""
import structlog
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .core.config import settings, get_token_config_summary
from .core.database import db
from .api import api_router
from .websockets import DeviceWebSocketHandler, DashboardWebSocketHandler, ChatbotWebSocketHandler

# Configurar logging estructurado
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestor del ciclo de vida de la aplicación.
    Se ejecuta al iniciar y al cerrar el servidor.
    """
    # Startup
    logger.info("application_starting", version="1.0.0")

    # Log de configuración de tokens
    token_config = get_token_config_summary()
    logger.info(
        "token_configuration_loaded",
        mode=token_config["mode"],
        ttl=token_config["ttl_human"],
        renewal_threshold=token_config["renewal_threshold_human"],
        check_interval=token_config["renewal_check_interval_human"],
        grace_period_days=token_config["grace_period_days"]
    )

    try:
        await db.connect()
        logger.info("database_pool_created")
    except Exception as e:
        logger.error("database_connection_failed", error=str(e))
        raise

    yield

    # Shutdown
    logger.info("application_shutting_down")
    await db.disconnect()
    logger.info("database_pool_closed")


# Crear aplicación FastAPI
app = FastAPI(
    title="Sistema de Monitoreo de Transporte",
    description="API REST y WebSocket para monitoreo de transporte y seguridad vial",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers de API REST
app.include_router(api_router)


# ==================== WebSocket Endpoints ====================

@app.websocket("/ws/device")
async def websocket_device_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint para dispositivos GPS.

    Protocolo:
    1. Dispositivo se conecta
    2. Envía mensaje AUTH con token y device_id
    3. Si autenticación exitosa, puede enviar mensajes POS
    4. Servidor envía ACK por cada posición recibida
    5. Si se detecta evento, se incluye en el ACK
    """
    handler = DeviceWebSocketHandler(websocket)
    await handler.handle()


@app.websocket("/ws/dashboard")
async def websocket_dashboard_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint para dashboards (clientes de monitoreo).

    Protocolo:
    1. Dashboard se conecta
    2. Envía mensaje SUBSCRIBE con lista de unidad_ids
    3. Servidor envía POSITION_UPDATE y EVENT_ALERT para unidades suscritas
    4. Dashboard puede enviar UNSUBSCRIBE para dejar de recibir updates
    5. Dashboard puede enviar PING para mantener conexión activa
    """
    handler = DashboardWebSocketHandler(websocket)
    await handler.handle()


@app.websocket("/ws/chatbot")
async def websocket_chatbot_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint para el chatbot de asistencia.

    Protocolo:
    1. Cliente se conecta
    2. Recibe mensaje de bienvenida automáticamente
    3. Envía mensaje USER_MESSAGE con texto
    4. Recibe respuesta BOT_MESSAGE
    5. Puede enviar PING para mantener conexión activa
    """
    handler = ChatbotWebSocketHandler(websocket)
    await handler.handle()


# ==================== Root Endpoint ====================

@app.get("/")
async def root():
    """Endpoint raíz con información básica"""
    return {
        "service": "Sistema de Monitoreo de Transporte",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "api_docs": "/docs",
            "api_redoc": "/redoc",
            "api_base": "/api/v1",
            "websocket_devices": "/ws/device",
            "websocket_dashboards": "/ws/dashboard",
            "websocket_chatbot": "/ws/chatbot",
            "health": "/api/v1/health",
            "status": "/api/v1/status",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
