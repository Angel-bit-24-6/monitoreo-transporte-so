"""
Handler WebSocket para dashboards (clientes de monitoreo).
"""
import structlog
import uuid
from fastapi import WebSocket, WebSocketDisconnect
import json

from ..models.schemas import (
    WSMessageType,
    PingMessage,
    SubscribeMessage,
    UnsubscribeMessage,
    PongResponse,
    ErrorResponse,
)
from .connection_manager import connection_manager

logger = structlog.get_logger()


class DashboardWebSocketHandler:
    """Handler para conexiones WebSocket de dashboards"""

    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.session_id = str(uuid.uuid4())

    async def handle(self):
        """Manejar conexión WebSocket de dashboard"""
        try:
            # Conectar dashboard
            await connection_manager.connect_dashboard(self.websocket, self.session_id)

            logger.info("dashboard_websocket_connected", session_id=self.session_id)

            # Loop de mensajes
            await self._message_loop()

        except WebSocketDisconnect:
            logger.info("dashboard_websocket_disconnected", session_id=self.session_id)
        except Exception as e:
            logger.error(
                "dashboard_websocket_error",
                session_id=self.session_id,
                error=str(e),
                exc_info=True,
            )
        finally:
            await connection_manager.disconnect_dashboard(self.session_id)

    async def _message_loop(self):
        """Loop principal para procesar mensajes del dashboard"""
        while True:
            try:
                data = await self.websocket.receive_json()
                message_type = data.get("type")

                if message_type == WSMessageType.SUBSCRIBE:
                    await self._handle_subscribe(data)
                elif message_type == WSMessageType.UNSUBSCRIBE:
                    await self._handle_unsubscribe(data)
                elif message_type == WSMessageType.PING:
                    await self._handle_ping()
                else:
                    logger.warning(
                        "unknown_message_type_dashboard",
                        type=message_type,
                        session_id=self.session_id,
                    )
                    response = ErrorResponse(
                        message=f"Tipo de mensaje desconocido: {message_type}",
                        code="UNKNOWN_MESSAGE_TYPE",
                    )
                    await self.websocket.send_json(response.model_dump())

            except json.JSONDecodeError as e:
                logger.error(
                    "json_decode_error_dashboard",
                    session_id=self.session_id,
                    error=str(e),
                )
                response = ErrorResponse(
                    message="JSON inválido", code="INVALID_JSON"
                )
                await self.websocket.send_json(response.model_dump())

    async def _handle_subscribe(self, data: dict):
        """Procesar suscripción a unidades"""
        try:
            sub_msg = SubscribeMessage(**data)
            await connection_manager.subscribe_dashboard(
                self.session_id, sub_msg.unidad_ids
            )

            # Enviar confirmación
            response = {
                "type": "SUBSCRIBED",
                "unidad_ids": sub_msg.unidad_ids,
                "message": f"Suscrito a {len(sub_msg.unidad_ids)} unidades",
            }
            await self.websocket.send_json(response)

            # Enviar estado de conexión actual de cada unidad
            for unidad_id in sub_msg.unidad_ids:
                is_connected = connection_manager.is_device_connected(unidad_id)
                state_msg = {
                    "type": "CONNECTION_STATE",
                    "unidad_id": unidad_id,
                    "is_connected": is_connected,
                }
                await self.websocket.send_json(state_msg)

        except Exception as e:
            logger.error(
                "handle_subscribe_error",
                session_id=self.session_id,
                error=str(e),
                exc_info=True,
            )
            response = ErrorResponse(
                message="Error al suscribirse", code="SUBSCRIBE_ERROR"
            )
            await self.websocket.send_json(response.model_dump())

    async def _handle_unsubscribe(self, data: dict):
        """Procesar desuscripción de unidades"""
        try:
            unsub_msg = UnsubscribeMessage(**data)
            await connection_manager.unsubscribe_dashboard(
                self.session_id, unsub_msg.unidad_ids
            )

            # Enviar confirmación
            response = {
                "type": "UNSUBSCRIBED",
                "unidad_ids": unsub_msg.unidad_ids,
                "message": f"Desuscrito de {len(unsub_msg.unidad_ids)} unidades",
            }
            await self.websocket.send_json(response)

        except Exception as e:
            logger.error(
                "handle_unsubscribe_error",
                session_id=self.session_id,
                error=str(e),
                exc_info=True,
            )
            response = ErrorResponse(
                message="Error al desuscribirse", code="UNSUBSCRIBE_ERROR"
            )
            await self.websocket.send_json(response.model_dump())

    async def _handle_ping(self):
        """Responder a heartbeat ping"""
        response = PongResponse()
        await self.websocket.send_json(response.model_dump())
