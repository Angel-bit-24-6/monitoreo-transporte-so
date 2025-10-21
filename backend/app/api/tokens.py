"""
API endpoints para gestión de tokens de autenticación.
"""
from fastapi import APIRouter, HTTPException
import structlog

from ..models.schemas import TokenCreateRequest, TokenCreateResponse
from ..services.auth_service import AuthService

logger = structlog.get_logger()
router = APIRouter(prefix="/tokens", tags=["Tokens"])


@router.post("", response_model=TokenCreateResponse, status_code=201)
async def create_token(request: TokenCreateRequest):
    """
    Crear nuevo token para un dispositivo.

    **IMPORTANTE**: El token se muestra UNA SOLA VEZ.
    Guárdelo de forma segura.
    """
    try:
        result = await AuthService.create_token(
            unidad_id=request.unidad_id,
            device_id=request.device_id,
            ttl_seconds=request.ttl_seconds,
            revoke_old=request.revoke_old,
        )

        if not result:
            raise HTTPException(
                status_code=500, detail="Error al crear token"
            )

        token_plain, token_id, expires_at = result

        return TokenCreateResponse(
            token_plain=token_plain,
            token_id=token_id,
            unidad_id=request.unidad_id,
            device_id=request.device_id,
            expires_at=expires_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("create_token_api_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Error al crear token")


@router.delete("/revoke", status_code=204)
async def revoke_token(token: str):
    """
    Revocar un token específico.

    Args:
        token: Token en texto plano a revocar
    """
    try:
        success = await AuthService.revoke_token(token)

        if not success:
            raise HTTPException(
                status_code=404, detail="Token no encontrado o ya revocado"
            )

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error("revoke_token_api_error", error=str(e))
        raise HTTPException(status_code=500, detail="Error al revocar token")


@router.delete("/device/{unidad_id}/{device_id}", status_code=200)
async def revoke_device_tokens(unidad_id: str, device_id: str):
    """
    Revocar todos los tokens de un dispositivo específico.

    Args:
        unidad_id: ID de la unidad
        device_id: ID del dispositivo
    """
    try:
        count = await AuthService.revoke_tokens_for_device(unidad_id, device_id)

        return {
            "message": f"Tokens revocados: {count}",
            "count": count,
            "unidad_id": unidad_id,
            "device_id": device_id,
        }

    except Exception as e:
        logger.error("revoke_device_tokens_api_error", error=str(e))
        raise HTTPException(
            status_code=500, detail="Error al revocar tokens del dispositivo"
        )
