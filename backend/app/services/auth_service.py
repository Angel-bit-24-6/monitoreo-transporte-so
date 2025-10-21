"""
Servicio de autenticación y gestión de tokens.
"""
import structlog
from typing import Optional, Tuple
from datetime import datetime
from ..core.database import db
from ..core.config import settings

logger = structlog.get_logger()


class AuthService:
    """Servicio para autenticación de dispositivos"""

    @staticmethod
    async def verify_token(unidad_id: str, token_plain: str) -> bool:
        """
        Verificar token de unidad usando la función de PostgreSQL.

        Args:
            unidad_id: ID de la unidad
            token_plain: Token en texto plano

        Returns:
            True si el token es válido, False en caso contrario
        """
        try:
            result = await db.fetch_one(
                "SELECT fn_verify_unidad_token($1, $2) as valid",
                unidad_id,
                token_plain,
            )
            is_valid = result["valid"] if result else False

            if is_valid:
                logger.info("token_verified", unidad_id=unidad_id)
            else:
                logger.warning("token_verification_failed", unidad_id=unidad_id)

            return is_valid
        except Exception as e:
            logger.error("token_verification_error", unidad_id=unidad_id, error=str(e))
            return False

    @staticmethod
    async def create_token(
        unidad_id: str,
        device_id: str,
        ttl_seconds: int = 86400 * 30,
        revoke_old: bool = False,
    ) -> Optional[Tuple[str, int, Optional[datetime]]]:
        """
        Crear nuevo token para un dispositivo.

        Args:
            unidad_id: ID de la unidad
            device_id: ID del dispositivo
            ttl_seconds: Tiempo de vida del token en segundos
            revoke_old: Si True, revoca tokens antiguos del mismo dispositivo

        Returns:
            Tupla (token_plain, token_id, expires_at) o None si falla
        """
        try:
            result = await db.fetch_one(
                """
                SELECT token_plain, token_id,
                       CASE
                           WHEN $3 > 0 THEN now() + ($3 || ' seconds')::interval
                           ELSE NULL
                       END as expires_at
                FROM fn_create_unidad_token_for_device($1, $2, $3, $4)
                """,
                unidad_id,
                device_id,
                ttl_seconds,
                revoke_old,
            )

            if result:
                logger.info(
                    "token_created",
                    unidad_id=unidad_id,
                    device_id=device_id,
                    token_id=result["token_id"],
                )
                return (
                    result["token_plain"],
                    result["token_id"],
                    result["expires_at"],
                )
            return None
        except Exception as e:
            logger.error(
                "token_creation_error",
                unidad_id=unidad_id,
                device_id=device_id,
                error=str(e),
            )
            return None

    @staticmethod
    async def revoke_token(token_plain: str) -> bool:
        """
        Revocar token específico.

        Args:
            token_plain: Token en texto plano

        Returns:
            True si se revocó, False en caso contrario
        """
        try:
            result = await db.fetch_one(
                "SELECT fn_revoke_token_by_plain($1) as revoked", token_plain
            )
            revoked = result["revoked"] if result else False

            if revoked:
                logger.info("token_revoked")
            else:
                logger.warning("token_revocation_failed")

            return revoked
        except Exception as e:
            logger.error("token_revocation_error", error=str(e))
            return False

    @staticmethod
    async def revoke_tokens_for_device(unidad_id: str, device_id: str) -> int:
        """
        Revocar todos los tokens de un dispositivo específico.

        Args:
            unidad_id: ID de la unidad
            device_id: ID del dispositivo

        Returns:
            Número de tokens revocados
        """
        try:
            result = await db.fetch_one(
                "SELECT fn_revoke_tokens_for_device($1, $2) as count",
                unidad_id,
                device_id,
            )
            count = result["count"] if result else 0

            logger.info(
                "device_tokens_revoked",
                unidad_id=unidad_id,
                device_id=device_id,
                count=count,
            )
            return count
        except Exception as e:
            logger.error(
                "device_tokens_revocation_error",
                unidad_id=unidad_id,
                device_id=device_id,
                error=str(e),
            )
            return 0

    @staticmethod
    async def cleanup_expired_tokens(older_than_days: int = 30) -> int:
        """
        Limpiar tokens expirados y revocados antiguos.

        Args:
            older_than_days: Eliminar tokens más antiguos que este número de días

        Returns:
            Número de tokens eliminados
        """
        try:
            result = await db.fetch_one(
                "SELECT fn_cleanup_expired_tokens($1) as deleted", older_than_days
            )
            deleted = result["deleted"] if result else 0

            logger.info("expired_tokens_cleaned", count=deleted)
            return deleted
        except Exception as e:
            logger.error("token_cleanup_error", error=str(e))
            return 0

    @staticmethod
    async def get_unidad_info(unidad_id: str) -> Optional[dict]:
        """
        Obtener información de una unidad.

        Args:
            unidad_id: ID de la unidad

        Returns:
            Diccionario con información de la unidad o None
        """
        try:
            result = await db.fetch_one(
                """
                SELECT id, placa, chofer, activo, created_at, updated_at
                FROM unidad
                WHERE id = $1
                """,
                unidad_id,
            )
            return dict(result) if result else None
        except Exception as e:
            logger.error("get_unidad_error", unidad_id=unidad_id, error=str(e))
            return None

    @staticmethod
    async def get_token_info(unidad_id: str, device_id: str) -> Optional[dict]:
        """
        Obtener información del token más reciente de un dispositivo.

        NOTA: Para renovación automática, devolvemos el token más reciente aunque
        haya expirado, para poder calcular cuándo renovar.

        Args:
            unidad_id: ID de la unidad
            device_id: ID del dispositivo

        Returns:
            Diccionario con info del token o None
        """
        try:
            result = await db.fetch_one(
                """
                SELECT id, unidad_id, device_id, expires_at, created_at, last_used, revoked
                FROM unidad_token
                WHERE unidad_id = $1
                  AND device_id = $2
                  AND revoked = FALSE
                ORDER BY created_at DESC
                LIMIT 1
                """,
                unidad_id,
                device_id,
            )

            if result:
                logger.debug(
                    "token_info_retrieved",
                    unidad_id=unidad_id,
                    device_id=device_id,
                    token_id=result["id"],
                    expires_at=result["expires_at"]
                )

            return dict(result) if result else None
        except Exception as e:
            logger.error("get_token_info_error",
                        unidad_id=unidad_id,
                        device_id=device_id,
                        error=str(e),
                        exc_info=True)
            return None

    @staticmethod
    async def should_renew_token(
        unidad_id: str,
        device_id: str,
        renewal_threshold_minutes: Optional[int] = None
    ) -> bool:
        """
        Verificar si un token debe renovarse basado en su tiempo de expiración.

        Args:
            unidad_id: ID de la unidad
            device_id: ID del dispositivo
            renewal_threshold_minutes: Minutos antes de expiración para renovar.
                                      Si es None, usa configuración de .env

        Returns:
            True si debe renovarse, False en caso contrario
        """
        # Usar configuración global si no se especifica
        if renewal_threshold_minutes is None:
            renewal_threshold_minutes = settings.TOKEN_RENEWAL_THRESHOLD_MINUTES

        try:
            token_info = await AuthService.get_token_info(unidad_id, device_id)

            if not token_info:
                logger.warning(
                    "token_info_not_found_for_renewal_check",
                    unidad_id=unidad_id,
                    device_id=device_id
                )
                return False

            expires_at = token_info.get("expires_at")

            if not expires_at:
                # Token sin expiración, no necesita renovación
                logger.debug(
                    "token_no_expiration_set",
                    unidad_id=unidad_id,
                    device_id=device_id
                )
                return False

            # Calcular tiempo hasta expiración
            from datetime import datetime, timedelta
            now = datetime.utcnow().replace(tzinfo=expires_at.tzinfo)
            time_until_expiry = (expires_at - now).total_seconds() / 60  # minutos

            should_renew = time_until_expiry <= renewal_threshold_minutes

            # LOG SIEMPRE, no solo cuando should_renew es True
            logger.info(
                "token_renewal_check",
                unidad_id=unidad_id,
                device_id=device_id,
                minutes_until_expiry=round(time_until_expiry, 2),
                threshold_minutes=renewal_threshold_minutes,
                should_renew=should_renew
            )

            return should_renew

        except Exception as e:
            logger.error("should_renew_token_error",
                        unidad_id=unidad_id,
                        device_id=device_id,
                        error=str(e),
                        exc_info=True)
            return False
