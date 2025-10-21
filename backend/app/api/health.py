"""
API endpoint para health check y estado del sistema.
"""
from fastapi import APIRouter, HTTPException
import structlog

from ..models.schemas import HealthResponse
from ..core.database import db
from ..websockets.connection_manager import connection_manager

logger = structlog.get_logger()
router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check del sistema"""
    try:
        # Verificar conexión a base de datos
        await db.fetch_one("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        logger.error("health_check_db_error", error=str(e))
        db_status = "unhealthy"

    return HealthResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        database=db_status,
    )


@router.get("/status")
async def system_status():
    """Estado detallado del sistema"""
    try:
        # Database stats
        db_stats = await db.fetch_one(
            """
            SELECT
                (SELECT COUNT(*) FROM unidad WHERE activo = TRUE) as active_units,
                (SELECT COUNT(*) FROM evento WHERE ts >= now() - interval '24 hours') as events_24h,
                (SELECT COUNT(*) FROM posicion WHERE ts >= now() - interval '1 hour') as positions_1h
            """
        )

        # WebSocket stats
        ws_stats = {
            "connected_devices": len(connection_manager.device_connections),
            "connected_dashboards": connection_manager.get_dashboard_count(),
            "devices": connection_manager.get_connected_devices(),
        }

        return {
            "status": "operational",
            "database": {
                "status": "healthy",
                "active_units": db_stats["active_units"],
                "events_last_24h": db_stats["events_24h"],
                "positions_last_hour": db_stats["positions_1h"],
            },
            "websockets": ws_stats,
        }

    except Exception as e:
        logger.error("system_status_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Error al obtener estado del sistema")
