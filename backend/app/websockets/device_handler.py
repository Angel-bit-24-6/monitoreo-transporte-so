"""
Handler WebSocket para dispositivos GPS.
"""
import asyncio
import structlog
from fastapi import WebSocket, WebSocketDisconnect
from typing import Optional
from datetime import datetime
import json

from ..models.schemas import (
    WSMessageType,
    AuthMessage,
    PositionMessage,
    PingMessage,
    AuthOKResponse,
    AuthFailedResponse,
    AckResponse,
    ErrorResponse,
    PongResponse,
    PositionUpdateResponse,
    EventAlertResponse,
    TokenRenewalResponse,
    TokenRenewalAckMessage,
)
from ..services.auth_service import AuthService
from ..services.position_service import PositionService
from .connection_manager import connection_manager, WebSocketConnection, ClientType
from ..core.config import settings

logger = structlog.get_logger()


class DeviceWebSocketHandler:
    """Handler para conexiones WebSocket de dispositivos GPS"""

    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.device_id: Optional[str] = None
        self.unidad_id: Optional[str] = None
        self.authenticated = False
        self.running = True
        self.renewal_task: Optional[asyncio.Task] = None

    async def handle(self):
        """Manejar conexión WebSocket de dispositivo"""
        try:
            # Aceptar conexión WebSocket
            await self.websocket.accept()

            # Esperar autenticación (ANTES de registrar en connection_manager)
            authenticated = await self._authenticate()
            if not authenticated:
                await self.websocket.close(code=4001, reason="Authentication failed")
                return

            # Registrar dispositivo en el gestor (SIN llamar accept() de nuevo)
            async with connection_manager._lock:
                connection = WebSocketConnection(
                    websocket=self.websocket,
                    client_type=ClientType.DEVICE,
                    client_id=self.device_id,
                    unidad_id=self.unidad_id,
                )
                connection_manager.device_connections[self.device_id] = connection

            # Notificar a dashboards que esta unidad se conectó
            await connection_manager.broadcast_connection_state(self.unidad_id, is_connected=True)

            logger.info(
                "device_connected",
                unidad_id=self.unidad_id,
                device_id=self.device_id,
                total_devices=len(connection_manager.device_connections),
            )

            # Iniciar tarea de verificación de renovación de token
            self.renewal_task = asyncio.create_task(self._token_renewal_checker())

            # Loop principal de mensajes
            await self._message_loop()

        except WebSocketDisconnect:
            logger.info(
                "device_websocket_disconnected",
                unidad_id=self.unidad_id,
                device_id=self.device_id,
            )
        except Exception as e:
            logger.error(
                "device_websocket_error",
                unidad_id=self.unidad_id,
                device_id=self.device_id,
                error=str(e),
                exc_info=True,
            )
        finally:
            # Detener tarea de renovación
            self.running = False
            if self.renewal_task:
                self.renewal_task.cancel()
                try:
                    await self.renewal_task
                except asyncio.CancelledError:
                    pass

            if self.device_id:
                await connection_manager.disconnect_device(self.device_id)

    async def _authenticate(self) -> bool:
        """
        Proceso de autenticación inicial.
        Espera mensaje AUTH con token y device_id.
        """
        try:
            # Esperar mensaje de autenticación (timeout 30s)
            data = await asyncio.wait_for(self.websocket.receive_json(), timeout=30.0)

            # Validar mensaje AUTH
            auth_msg = AuthMessage(**data)

            # Extraer unidad_id del token (primeros caracteres antes del hash)
            # En producción, el token debería incluir metadata o usar otro método
            # Por ahora, buscaremos qué unidad corresponde al token
            unidad_id = await self._find_unidad_by_token(auth_msg.token)

            if not unidad_id:
                response = AuthFailedResponse(
                    message="Token inválido",
                    reason="No se encontró unidad asociada al token",
                )
                await self.websocket.send_json(response.model_dump())
                return False

            # Verificar token
            is_valid = await AuthService.verify_token(unidad_id, auth_msg.token)

            if not is_valid:
                response = AuthFailedResponse(
                    message="Autenticación fallida",
                    reason="Token inválido o expirado",
                )
                await self.websocket.send_json(response.model_dump())
                return False

            # Autenticación exitosa
            self.unidad_id = unidad_id
            self.device_id = auth_msg.device_id
            self.authenticated = True

            response = AuthOKResponse(
                unidad_id=unidad_id,
                message=f"Autenticación exitosa para {unidad_id}",
            )
            await self.websocket.send_json(response.model_dump())

            logger.info(
                "device_authenticated",
                unidad_id=unidad_id,
                device_id=auth_msg.device_id,
            )
            return True

        except asyncio.TimeoutError:
            logger.warning("authentication_timeout")
            return False
        except Exception as e:
            logger.error("authentication_error", error=str(e), exc_info=True)
            return False

    async def _find_unidad_by_token(self, token_plain: str) -> Optional[str]:
        """
        Buscar unidad_id asociada a un token.
        Nota: En producción, considera incluir unidad_id en el payload del token.
        """
        try:
            from ..core.database import db

            # Hash del token usando SHA256
            result = await db.fetch_one(
                """
                SELECT unidad_id
                FROM unidad_token
                WHERE token_hash = digest($1, 'sha256')
                  AND (expires_at IS NULL OR expires_at > now())
                  AND revoked = FALSE
                LIMIT 1
                """,
                token_plain,
            )
            return result["unidad_id"] if result else None
        except Exception as e:
            logger.error("find_unidad_by_token_error", error=str(e))
            return None

    async def _message_loop(self):
        """Loop principal para procesar mensajes del dispositivo"""
        while True:
            try:
                data = await self.websocket.receive_json()
                message_type = data.get("type")

                if message_type == WSMessageType.POS:
                    await self._handle_position(data)
                elif message_type == WSMessageType.PING:
                    await self._handle_ping()
                elif message_type == WSMessageType.TOKEN_RENEWAL_ACK:
                    await self._handle_token_renewal_ack(data)
                else:
                    logger.warning(
                        "unknown_message_type",
                        type=message_type,
                        unidad_id=self.unidad_id,
                    )
                    response = ErrorResponse(
                        message=f"Tipo de mensaje desconocido: {message_type}",
                        code="UNKNOWN_MESSAGE_TYPE",
                    )
                    await self.websocket.send_json(response.model_dump())

            except json.JSONDecodeError as e:
                logger.error("json_decode_error", unidad_id=self.unidad_id, error=str(e))
                response = ErrorResponse(
                    message="JSON inválido", code="INVALID_JSON"
                )
                await self.websocket.send_json(response.model_dump())

    async def _handle_position(self, data: dict):
        """Procesar mensaje de posición GPS"""
        try:
            # Validar mensaje
            pos_msg = PositionMessage(**data)

            # Insertar posición en DB y detectar eventos
            posicion_id, evento_id = await PositionService.insert_position_and_detect(
                unidad_id=self.unidad_id,
                ts=pos_msg.timestamp,
                lat=pos_msg.lat,
                lon=pos_msg.lon,
                speed=pos_msg.speed,
                heading=pos_msg.heading,
                seq=pos_msg.seq,
                raw_payload=data,
            )

            # Enviar ACK al dispositivo
            if posicion_id:
                response = AckResponse(
                    posicion_id=posicion_id,
                    event_id=evento_id,
                )
                await self.websocket.send_json(response.model_dump())

                # Broadcast a dashboards suscritos
                await self._broadcast_position_update(pos_msg, posicion_id)

                # Si hay evento, notificar también
                if evento_id:
                    await self._broadcast_event_alert(evento_id)

            else:
                response = ErrorResponse(
                    message="Error al insertar posición",
                    code="POSITION_INSERT_FAILED",
                )
                await self.websocket.send_json(response.model_dump())

        except Exception as e:
            logger.error(
                "handle_position_error",
                unidad_id=self.unidad_id,
                error=str(e),
                exc_info=True,
            )
            response = ErrorResponse(
                message="Error al procesar posición", code="POSITION_PROCESSING_ERROR"
            )
            await self.websocket.send_json(response.model_dump())

    async def _handle_ping(self):
        """Responder a heartbeat ping"""
        response = PongResponse()
        await self.websocket.send_json(response.model_dump())

    async def _broadcast_position_update(self, pos_msg: PositionMessage, posicion_id: int):
        """Enviar update de posición a dashboards suscritos"""
        update = PositionUpdateResponse(
            unidad_id=self.unidad_id,
            posicion_id=posicion_id,
            lat=pos_msg.lat,
            lon=pos_msg.lon,
            speed=pos_msg.speed,
            heading=pos_msg.heading,
            timestamp=pos_msg.timestamp,
        )
        await connection_manager.broadcast_to_unidad_subscribers(
            self.unidad_id, update.model_dump()
        )

    async def _broadcast_event_alert(self, evento_id: int):
        """Enviar alerta de evento a dashboards suscritos"""
        # Obtener detalles del evento
        event_details = await PositionService.get_event_details(evento_id)
        if not event_details:
            return

        alert = EventAlertResponse(
            unidad_id=self.unidad_id,
            event_id=evento_id,
            event_tipo=event_details["tipo"],
            detalle=event_details["detalle"],
            timestamp=event_details["ts"],
            posicion_id=event_details.get("posicion_id"),
        )
        await connection_manager.broadcast_to_unidad_subscribers(
            self.unidad_id, alert.model_dump()
        )

    async def _token_renewal_checker(self):
        """
        Tarea periódica para verificar si el token necesita renovación.
        Se ejecuta cada 60 segundos mientras la conexión esté activa.
        """
        logger.info(
            "token_renewal_checker_started",
            unidad_id=self.unidad_id,
            device_id=self.device_id
        )

        while self.running:
            try:
                # Verificar si necesita renovación (lee configuración desde .env)
                should_renew = await AuthService.should_renew_token(
                    self.unidad_id,
                    self.device_id
                    # No se pasa renewal_threshold_minutes, usa configuración de .env
                )

                if should_renew:
                    logger.info(
                        "initiating_token_renewal",
                        unidad_id=self.unidad_id,
                        device_id=self.device_id
                    )
                    await self._send_token_renewal()

                # Esperar intervalo configurable antes de la siguiente verificación
                await asyncio.sleep(settings.TOKEN_RENEWAL_CHECK_INTERVAL_SECONDS)

            except asyncio.CancelledError:
                logger.info(
                    "token_renewal_checker_cancelled",
                    unidad_id=self.unidad_id,
                    device_id=self.device_id
                )
                break
            except Exception as e:
                logger.error(
                    "token_renewal_checker_error",
                    unidad_id=self.unidad_id,
                    device_id=self.device_id,
                    error=str(e),
                    exc_info=True
                )

    async def _send_token_renewal(self):
        """
        Crear nuevo token y enviarlo al dispositivo.
        NO revoca el token antiguo (grace period).
        """
        try:
            # Crear nuevo token sin revocar el antiguo (lee TTL desde .env)
            new_token_data = await AuthService.create_token(
                self.unidad_id,
                self.device_id,
                ttl_seconds=settings.TOKEN_TTL_SECONDS,  # Lee desde .env
                revoke_old=False  # IMPORTANTE: No revocar para permitir grace period
            )

            if not new_token_data:
                logger.error(
                    "token_renewal_creation_failed",
                    unidad_id=self.unidad_id,
                    device_id=self.device_id
                )
                return

            token_plain, token_id, expires_at = new_token_data

            # Preparar mensaje de renovación
            renewal_msg = TokenRenewalResponse(
                new_token=token_plain,
                expires_at=expires_at,
                grace_period_days=settings.TOKEN_GRACE_PERIOD_DAYS,  # Lee desde .env
                message="Token renovado. Actualice su configuración."
            )

            # Enviar al dispositivo
            await self.websocket.send_json(renewal_msg.model_dump())

            logger.info(
                "token_renewal_sent",
                unidad_id=self.unidad_id,
                device_id=self.device_id,
                new_token_id=token_id,
                expires_at=expires_at
            )

        except Exception as e:
            logger.error(
                "send_token_renewal_error",
                unidad_id=self.unidad_id,
                device_id=self.device_id,
                error=str(e),
                exc_info=True
            )

    async def _handle_token_renewal_ack(self, data: dict):
        """
        Manejar confirmación de renovación de token desde el dispositivo.
        """
        try:
            # Validar mensaje
            ack_msg = TokenRenewalAckMessage(**data)

            logger.info(
                "token_renewal_acknowledged",
                unidad_id=self.unidad_id,
                device_id=self.device_id,
                new_token_saved=ack_msg.new_token_saved,
                message=ack_msg.message
            )

            # Aquí podrías agregar lógica adicional, como:
            # - Actualizar un campo en la BD indicando que el dispositivo confirmó
            # - Enviar notificación a dashboards
            # - Registrar el evento en una tabla de auditoría

        except Exception as e:
            logger.error(
                "handle_token_renewal_ack_error",
                unidad_id=self.unidad_id,
                device_id=self.device_id,
                error=str(e),
                exc_info=True
            )
