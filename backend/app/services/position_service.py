"""
Servicio para inserción y gestión de posiciones GPS.
"""
import structlog
from typing import Optional, Tuple
from datetime import datetime
from ..core.database import db

logger = structlog.get_logger()


class PositionService:
    """Servicio para gestión de posiciones"""

    @staticmethod
    async def insert_position_and_detect(
        unidad_id: str,
        ts: datetime,
        lat: float,
        lon: float,
        speed: Optional[float] = None,
        heading: Optional[float] = None,
        seq: Optional[int] = None,
        raw_payload: Optional[dict] = None,
    ) -> Tuple[Optional[int], Optional[int]]:
        """
        Insertar posición y detectar eventos automáticamente.

        Args:
            unidad_id: ID de la unidad
            ts: Timestamp de la posición
            lat: Latitud
            lon: Longitud
            speed: Velocidad en m/s
            heading: Rumbo en grados
            seq: Número de secuencia
            raw_payload: Payload JSON raw

        Returns:
            Tupla (posicion_id, evento_id) o (None, None) si falla
        """
        try:
            import json

            raw_json = json.dumps(raw_payload) if raw_payload else None

            result = await db.fetch_one(
                """
                SELECT posicion_id, created_event_id
                FROM fn_insert_position_and_detect($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                unidad_id,
                ts,
                lat,
                lon,
                speed,
                heading,
                seq,
                raw_json,
            )

            if result:
                posicion_id = result["posicion_id"]
                evento_id = result["created_event_id"]

                logger.info(
                    "position_inserted",
                    unidad_id=unidad_id,
                    posicion_id=posicion_id,
                    evento_id=evento_id,
                    has_event=evento_id is not None,
                )

                return (posicion_id, evento_id)

            return (None, None)
        except Exception as e:
            logger.error(
                "position_insert_error", unidad_id=unidad_id, error=str(e), exc_info=True
            )
            return (None, None)

    @staticmethod
    async def get_last_positions(limit: int = 100) -> list:
        """
        Obtener últimas posiciones de todas las unidades.

        Args:
            limit: Número máximo de posiciones por unidad

        Returns:
            Lista de posiciones
        """
        try:
            rows = await db.fetch_all(
                """
                SELECT DISTINCT ON (p.unidad_id)
                    p.id,
                    p.unidad_id,
                    p.ts,
                    ST_Y(p.geom::geometry) as lat,
                    ST_X(p.geom::geometry) as lon,
                    p.speed,
                    p.heading,
                    p.seq,
                    u.placa,
                    u.chofer
                FROM posicion p
                INNER JOIN unidad u ON u.id = p.unidad_id
                WHERE u.activo = TRUE
                ORDER BY p.unidad_id, p.ts DESC
                LIMIT $1
                """,
                limit,
            )
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error("get_last_positions_error", error=str(e))
            return []

    @staticmethod
    async def get_positions_by_unidad(
        unidad_id: str, limit: int = 100, offset: int = 0
    ) -> list:
        """
        Obtener posiciones históricas de una unidad específica.

        Args:
            unidad_id: ID de la unidad
            limit: Número máximo de registros
            offset: Offset para paginación

        Returns:
            Lista de posiciones
        """
        try:
            rows = await db.fetch_all(
                """
                SELECT
                    p.id,
                    p.unidad_id,
                    p.ts,
                    ST_Y(p.geom::geometry) as lat,
                    ST_X(p.geom::geometry) as lon,
                    p.speed,
                    p.heading,
                    p.seq
                FROM posicion p
                WHERE p.unidad_id = $1
                ORDER BY p.ts DESC
                LIMIT $2 OFFSET $3
                """,
                unidad_id,
                limit,
                offset,
            )
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(
                "get_positions_by_unidad_error", unidad_id=unidad_id, error=str(e)
            )
            return []

    @staticmethod
    async def get_event_details(evento_id: int) -> Optional[dict]:
        """
        Obtener detalles de un evento específico.

        Args:
            evento_id: ID del evento

        Returns:
            Diccionario con detalles del evento o None
        """
        try:
            result = await db.fetch_one(
                """
                SELECT
                    e.id,
                    e.unidad_id,
                    e.tipo,
                    e.detalle,
                    e.ts,
                    e.posicion_id,
                    e.metadata,
                    e.created_at,
                    ST_Y(p.geom::geometry) as lat,
                    ST_X(p.geom::geometry) as lon
                FROM evento e
                LEFT JOIN posicion p ON p.id = e.posicion_id
                WHERE e.id = $1
                """,
                evento_id,
            )
            return dict(result) if result else None
        except Exception as e:
            logger.error("get_event_details_error", evento_id=evento_id, error=str(e))
            return None
