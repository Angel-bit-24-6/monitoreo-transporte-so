from fastapi import APIRouter
from .unidades import router as unidades_router
from .tokens import router as tokens_router
from .rutas import router as rutas_router
from .eventos import router as eventos_router
from .health import router as health_router
from .pois import router as pois_router

# Router principal que agrupa todos los endpoints
api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health_router)
api_router.include_router(unidades_router)
api_router.include_router(tokens_router)
api_router.include_router(rutas_router)
api_router.include_router(eventos_router)
api_router.include_router(pois_router)

__all__ = ["api_router"]
