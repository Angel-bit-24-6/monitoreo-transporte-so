"""
Gestor de conexiones WebSocket para dispositivos GPS y dashboards.
"""
import asyncio
import structlog
from typing import Dict, Set, Optional
from fastapi import WebSocket
from datetime import datetime
from enum import Enum

logger = structlog.get_logger()


class ClientType(str, Enum):
    """Tipos de clientes WebSocket"""
    DEVICE = "device"
    DASHBOARD = "dashboard"


class WebSocketConnection:
    """Representa una conexión WebSocket individual"""

    def __init__(
        self,
        websocket: WebSocket,
        client_type: ClientType,
        client_id: str,
        unidad_id: Optional[str] = None,
    ):
        self.websocket = websocket
        self.client_type = client_type
        self.client_id = client_id  # session_id único
        self.unidad_id = unidad_id  # Para dispositivos: ID de la unidad
        self.connected_at = datetime.utcnow()
        self.last_ping = datetime.utcnow()
        self.subscriptions: Set[str] = set()  # Para dashboards: unidades suscritas


class ConnectionManager:
    """
    Gestor centralizado de todas las conexiones WebSocket.
    Separa dispositivos GPS de dashboards.
    """

    def __init__(self):
        # device_id -> WebSocketConnection
        self.device_connections: Dict[str, WebSocketConnection] = {}

        # session_id -> WebSocketConnection
        self.dashboard_connections: Dict[str, WebSocketConnection] = {}

        # unidad_id -> set de session_ids de dashboards suscritos
        self.unidad_subscribers: Dict[str, Set[str]] = {}

        self._lock = asyncio.Lock()

    async def connect_device(
        self, websocket: WebSocket, unidad_id: str, device_id: str
    ):
        """Conectar dispositivo GPS"""
        await websocket.accept()

        async with self._lock:
            connection = WebSocketConnection(
                websocket=websocket,
                client_type=ClientType.DEVICE,
                client_id=device_id,
                unidad_id=unidad_id,
            )
            self.device_connections[device_id] = connection

        logger.info(
            "device_connected",
            unidad_id=unidad_id,
            device_id=device_id,
            total_devices=len(self.device_connections),
        )

        # Notificar a dashboards que esta unidad se conectó
        await self.broadcast_connection_state(unidad_id, is_connected=True)

    async def disconnect_device(self, device_id: str):
        """Desconectar dispositivo GPS"""
        async with self._lock:
            connection = self.device_connections.pop(device_id, None)

        if connection:
            unidad_id = connection.unidad_id
            logger.info(
                "device_disconnected",
                unidad_id=unidad_id,
                device_id=device_id,
                total_devices=len(self.device_connections),
            )

            # Notificar a dashboards que esta unidad se desconectó
            await self.broadcast_connection_state(unidad_id, is_connected=False)

    async def connect_dashboard(self, websocket: WebSocket, session_id: str):
        """Conectar dashboard (cliente de monitoreo)"""
        await websocket.accept()

        async with self._lock:
            connection = WebSocketConnection(
                websocket=websocket,
                client_type=ClientType.DASHBOARD,
                client_id=session_id,
            )
            self.dashboard_connections[session_id] = connection

        logger.info(
            "dashboard_connected",
            session_id=session_id,
            total_dashboards=len(self.dashboard_connections),
        )

    async def disconnect_dashboard(self, session_id: str):
        """Desconectar dashboard"""
        async with self._lock:
            connection = self.dashboard_connections.pop(session_id, None)

        if connection:
            # Limpiar suscripciones
            for unidad_id in connection.subscriptions:
                if unidad_id in self.unidad_subscribers:
                    self.unidad_subscribers[unidad_id].discard(session_id)
                    if not self.unidad_subscribers[unidad_id]:
                        del self.unidad_subscribers[unidad_id]

            logger.info(
                "dashboard_disconnected",
                session_id=session_id,
                total_dashboards=len(self.dashboard_connections),
            )

    async def subscribe_dashboard(self, session_id: str, unidad_ids: list[str]):
        """Suscribir dashboard a updates de unidades específicas"""
        async with self._lock:
            connection = self.dashboard_connections.get(session_id)
            if not connection:
                return

            for unidad_id in unidad_ids:
                connection.subscriptions.add(unidad_id)

                if unidad_id not in self.unidad_subscribers:
                    self.unidad_subscribers[unidad_id] = set()
                self.unidad_subscribers[unidad_id].add(session_id)

        logger.info(
            "dashboard_subscribed",
            session_id=session_id,
            unidad_ids=unidad_ids,
            total_subscriptions=len(connection.subscriptions),
        )

    async def unsubscribe_dashboard(self, session_id: str, unidad_ids: list[str]):
        """Desuscribir dashboard de unidades"""
        async with self._lock:
            connection = self.dashboard_connections.get(session_id)
            if not connection:
                return

            for unidad_id in unidad_ids:
                connection.subscriptions.discard(unidad_id)

                if unidad_id in self.unidad_subscribers:
                    self.unidad_subscribers[unidad_id].discard(session_id)
                    if not self.unidad_subscribers[unidad_id]:
                        del self.unidad_subscribers[unidad_id]

        logger.info(
            "dashboard_unsubscribed",
            session_id=session_id,
            unidad_ids=unidad_ids,
        )

    async def send_to_device(self, device_id: str, message: dict):
        """Enviar mensaje a dispositivo específico"""
        connection = self.device_connections.get(device_id)
        if connection:
            try:
                await connection.websocket.send_json(message)
            except Exception as e:
                logger.error(
                    "send_to_device_error", device_id=device_id, error=str(e)
                )
                await self.disconnect_device(device_id)

    async def broadcast_to_unidad_subscribers(self, unidad_id: str, message: dict):
        """
        Enviar mensaje a todos los dashboards suscritos a una unidad específica.
        """
        subscriber_ids = self.unidad_subscribers.get(unidad_id, set()).copy()

        if not subscriber_ids:
            return

        tasks = []
        for session_id in subscriber_ids:
            connection = self.dashboard_connections.get(session_id)
            if connection:
                tasks.append(self._send_to_dashboard(session_id, message))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _send_to_dashboard(self, session_id: str, message: dict):
        """Enviar mensaje a dashboard específico"""
        connection = self.dashboard_connections.get(session_id)
        if connection:
            try:
                await connection.websocket.send_json(message)
            except Exception as e:
                logger.error(
                    "send_to_dashboard_error", session_id=session_id, error=str(e)
                )
                await self.disconnect_dashboard(session_id)

    async def broadcast_connection_state(self, unidad_id: str, is_connected: bool):
        """
        Notificar a dashboards sobre cambio de estado de conexión de una unidad.
        """
        message = {
            "type": "CONNECTION_STATE",
            "unidad_id": unidad_id,
            "is_connected": is_connected,
            "last_ping": datetime.utcnow().isoformat(),
        }
        await self.broadcast_to_unidad_subscribers(unidad_id, message)

    def is_device_connected(self, unidad_id: str) -> bool:
        """Verificar si una unidad tiene dispositivos conectados"""
        return any(
            conn.unidad_id == unidad_id
            for conn in self.device_connections.values()
        )

    def get_connected_devices(self) -> list[dict]:
        """Obtener lista de dispositivos conectados"""
        return [
            {
                "device_id": conn.client_id,
                "unidad_id": conn.unidad_id,
                "connected_at": conn.connected_at.isoformat(),
                "last_ping": conn.last_ping.isoformat(),
            }
            for conn in self.device_connections.values()
        ]

    def get_dashboard_count(self) -> int:
        """Obtener número de dashboards conectados"""
        return len(self.dashboard_connections)


# Instancia global del gestor de conexiones
connection_manager = ConnectionManager()
