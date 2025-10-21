"""
Modelos Pydantic para validación de mensajes WebSocket y API REST.
"""
from pydantic import BaseModel, Field, validator, ConfigDict
from typing import Optional, Literal, Any
from datetime import datetime
from enum import Enum


# Configuración global para serialización de datetime
class BaseModelWithDatetime(BaseModel):
    """BaseModel con configuración para serializar datetime a ISO string"""
    model_config = ConfigDict(
        # Modo de serialización para JSON
        ser_json_timedelta='iso8601',
    )

    def model_dump(self, **kwargs):
        """Override model_dump para convertir datetime a string"""
        data = super().model_dump(**kwargs)
        return self._serialize_datetimes(data)

    @staticmethod
    def _serialize_datetimes(data):
        """Recursivamente serializar datetime a ISO string"""
        if isinstance(data, dict):
            return {k: BaseModelWithDatetime._serialize_datetimes(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [BaseModelWithDatetime._serialize_datetimes(item) for item in data]
        elif isinstance(data, datetime):
            return data.isoformat()
        return data


class EventoTipo(str, Enum):
    """Tipos de eventos del sistema"""
    OUT_OF_BOUND = "OUT_OF_BOUND"
    STOP_LONG = "STOP_LONG"
    SPEEDING = "SPEEDING"
    GENERAL_ALERT = "GENERAL_ALERT"
    INFO = "INFO"


# ==================== Mensajes WebSocket (Cliente → Servidor) ====================

class WSMessageType(str, Enum):
    """Tipos de mensajes WebSocket"""
    AUTH = "AUTH"
    POS = "POS"
    PING = "PING"
    SUBSCRIBE = "SUBSCRIBE"
    UNSUBSCRIBE = "UNSUBSCRIBE"
    TOKEN_RENEWAL_ACK = "TOKEN_RENEWAL_ACK"  # Confirmación de renovación desde dispositivo


class AuthMessage(BaseModel):
    """Mensaje de autenticación desde dispositivo GPS"""
    type: Literal[WSMessageType.AUTH] = WSMessageType.AUTH
    token: str = Field(..., min_length=32, max_length=256)
    device_id: str = Field(..., min_length=1, max_length=100)


class PositionMessage(BaseModel):
    """Mensaje de posición GPS"""
    type: Literal[WSMessageType.POS] = WSMessageType.POS
    lat: float = Field(..., ge=-90, le=90, description="Latitud")
    lon: float = Field(..., ge=-180, le=180, description="Longitud")
    speed: Optional[float] = Field(None, ge=0, description="Velocidad en m/s")
    heading: Optional[float] = Field(None, ge=0, lt=360, description="Rumbo en grados")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    seq: Optional[int] = Field(None, ge=0, description="Número de secuencia")

    @validator('timestamp', pre=True)
    def parse_timestamp(cls, v):
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace('Z', '+00:00'))
        return v


class PingMessage(BaseModel):
    """Mensaje de heartbeat"""
    type: Literal[WSMessageType.PING] = WSMessageType.PING


class SubscribeMessage(BaseModel):
    """Mensaje para suscribirse a updates de una unidad (dashboard)"""
    type: Literal[WSMessageType.SUBSCRIBE] = WSMessageType.SUBSCRIBE
    unidad_ids: list[str] = Field(..., min_items=1, description="IDs de unidades a monitorear")


class UnsubscribeMessage(BaseModel):
    """Mensaje para desuscribirse"""
    type: Literal[WSMessageType.UNSUBSCRIBE] = WSMessageType.UNSUBSCRIBE
    unidad_ids: list[str]


class TokenRenewalAckMessage(BaseModel):
    """Confirmación de que dispositivo recibió y guardó el nuevo token"""
    type: Literal[WSMessageType.TOKEN_RENEWAL_ACK] = WSMessageType.TOKEN_RENEWAL_ACK
    new_token_saved: bool
    device_id: str
    message: Optional[str] = None


# ==================== Mensajes WebSocket (Servidor → Cliente) ====================

class WSResponseType(str, Enum):
    """Tipos de respuestas del servidor"""
    AUTH_OK = "AUTH_OK"
    AUTH_FAILED = "AUTH_FAILED"
    ACK = "ACK"
    ERROR = "ERROR"
    PONG = "PONG"
    POSITION_UPDATE = "POSITION_UPDATE"
    EVENT_ALERT = "EVENT_ALERT"
    CONNECTION_STATE = "CONNECTION_STATE"
    TOKEN_RENEWAL = "TOKEN_RENEWAL"


class AuthOKResponse(BaseModel):
    """Respuesta exitosa de autenticación"""
    type: Literal[WSResponseType.AUTH_OK] = WSResponseType.AUTH_OK
    unidad_id: str
    message: str = "Autenticación exitosa"


class AuthFailedResponse(BaseModel):
    """Respuesta fallida de autenticación"""
    type: Literal[WSResponseType.AUTH_FAILED] = WSResponseType.AUTH_FAILED
    message: str
    reason: str


class AckResponse(BaseModelWithDatetime):
    """Confirmación de recepción de posición"""
    type: Literal[WSResponseType.ACK] = WSResponseType.ACK
    posicion_id: int
    event_id: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    """Mensaje de error"""
    type: Literal[WSResponseType.ERROR] = WSResponseType.ERROR
    message: str
    code: Optional[str] = None


class PongResponse(BaseModelWithDatetime):
    """Respuesta a ping"""
    type: Literal[WSResponseType.PONG] = WSResponseType.PONG
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PositionUpdateResponse(BaseModelWithDatetime):
    """Update de posición enviado al dashboard"""
    type: Literal[WSResponseType.POSITION_UPDATE] = WSResponseType.POSITION_UPDATE
    unidad_id: str
    posicion_id: int
    lat: float
    lon: float
    speed: Optional[float]
    heading: Optional[float]
    timestamp: datetime


class EventAlertResponse(BaseModelWithDatetime):
    """Alerta de evento enviada al dashboard"""
    type: Literal[WSResponseType.EVENT_ALERT] = WSResponseType.EVENT_ALERT
    unidad_id: str
    event_id: int
    event_tipo: EventoTipo
    detalle: str
    timestamp: datetime
    posicion_id: Optional[int] = None


class ConnectionStateResponse(BaseModelWithDatetime):
    """Estado de conexión de una unidad"""
    type: Literal[WSResponseType.CONNECTION_STATE] = WSResponseType.CONNECTION_STATE
    unidad_id: str
    is_connected: bool
    last_ping: Optional[datetime] = None


class TokenRenewalResponse(BaseModelWithDatetime):
    """Notificación de renovación de token enviada al dispositivo"""
    type: Literal[WSResponseType.TOKEN_RENEWAL] = WSResponseType.TOKEN_RENEWAL
    new_token: str
    expires_at: datetime
    grace_period_days: int = 7
    message: str = "Token renovado. Actualice su configuración."


# ==================== Modelos REST API ====================

class UnidadCreate(BaseModel):
    """Crear nueva unidad"""
    id: str = Field(..., min_length=1, max_length=100)
    placa: str = Field(..., min_length=1, max_length=50)
    chofer: Optional[str] = Field(None, max_length=200)
    activo: bool = True


class UnidadResponse(BaseModel):
    """Respuesta de unidad"""
    id: str
    placa: str
    chofer: Optional[str]
    activo: bool
    created_at: datetime
    updated_at: datetime


class TokenCreateRequest(BaseModel):
    """Crear token para dispositivo"""
    unidad_id: str
    device_id: str
    ttl_seconds: int = Field(86400 * 30, ge=600, le=86400 * 365)  # 10 min a 1 año
    revoke_old: bool = False


class TokenCreateResponse(BaseModel):
    """Respuesta con token creado"""
    token_plain: str
    token_id: int
    unidad_id: str
    device_id: str
    expires_at: Optional[datetime]
    message: str = "Token creado exitosamente. Guárdelo de forma segura, no se mostrará nuevamente."


class RutaCreate(BaseModel):
    """Crear nueva ruta"""
    nombre: str = Field(..., min_length=1)
    descripcion: Optional[str] = None
    coordinates: list[tuple[float, float]] = Field(..., min_items=2, description="Lista de [lon, lat]")


class RutaResponse(BaseModel):
    """Respuesta de ruta"""
    id: int
    nombre: str
    descripcion: Optional[str]
    distancia_m: Optional[float]
    created_at: datetime


class EventoResponse(BaseModelWithDatetime):
    """Respuesta de evento"""
    id: int
    unidad_id: Optional[str]
    tipo: EventoTipo
    detalle: Optional[str]
    ts: datetime
    posicion_id: Optional[int]
    metadata: Optional[dict]
    created_at: datetime


class PosicionResponse(BaseModel):
    """Respuesta de posición"""
    id: int
    unidad_id: str
    ts: datetime
    lat: float
    lon: float
    speed: Optional[float]
    heading: Optional[float]
    seq: Optional[int]


class UnidadRutaAssignmentCreate(BaseModel):
    """Asignar ruta a unidad"""
    unidad_id: str
    ruta_id: int
    start_ts: datetime = Field(default_factory=datetime.utcnow)


class HealthResponse(BaseModel):
    """Respuesta de health check"""
    status: str
    database: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
