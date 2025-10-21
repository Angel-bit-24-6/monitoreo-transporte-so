"""
API endpoints para consulta de eventos.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta
import structlog
import json

from ..models.schemas import EventoResponse, EventoTipo
from ..core.database import db

logger = structlog.get_logger()
router = APIRouter(prefix="/eventos", tags=["Eventos"])


@router.get("", response_model=List[EventoResponse])
async def list_eventos(
    unidad_id: Optional[str] = None,
    tipo: Optional[EventoTipo] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """
    Listar eventos con filtros opcionales.

    Parámetros:
    - unidad_id: Filtrar por unidad específica
    - tipo: Filtrar por tipo de evento
    - start_date: Fecha inicio (ISO 8601)
    - end_date: Fecha fin (ISO 8601)
    """
    try:
        # Construcción dinámica de query
        conditions = []
        params = []
        param_idx = 1

        if unidad_id:
            conditions.append(f"unidad_id = ${param_idx}")
            params.append(unidad_id)
            param_idx += 1

        if tipo:
            conditions.append(f"tipo = ${param_idx}")
            params.append(tipo.value)
            param_idx += 1

        if start_date:
            conditions.append(f"ts >= ${param_idx}")
            params.append(start_date)
            param_idx += 1

        if end_date:
            conditions.append(f"ts <= ${param_idx}")
            params.append(end_date)
            param_idx += 1

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        params.extend([limit, offset])

        query = f"""
            SELECT
                id,
                unidad_id,
                tipo,
                detalle,
                ts,
                posicion_id,
                metadata,
                created_at
            FROM evento
            {where_clause}
            ORDER BY ts DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """

        rows = await db.fetch_all(query, *params)

        # Convertir metadata de string JSON a dict si es necesario
        result = []
        for row in rows:
            row_dict = dict(row)
            # asyncpg devuelve JSONB como string, convertirlo a dict
            if row_dict.get('metadata') and isinstance(row_dict['metadata'], str):
                row_dict['metadata'] = json.loads(row_dict['metadata'])
            result.append(row_dict)

        return result

    except Exception as e:
        logger.error("list_eventos_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Error al listar eventos")


@router.get("/{evento_id}", response_model=EventoResponse)
async def get_evento(evento_id: int):
    """Obtener detalles de un evento específico"""
    try:
        row = await db.fetch_one(
            """
            SELECT
                id,
                unidad_id,
                tipo,
                detalle,
                ts,
                posicion_id,
                metadata,
                created_at
            FROM evento
            WHERE id = $1
            """,
            evento_id,
        )

        if not row:
            raise HTTPException(status_code=404, detail="Evento no encontrado")

        row_dict = dict(row)
        # Convertir metadata de string JSON a dict si es necesario
        if row_dict.get('metadata') and isinstance(row_dict['metadata'], str):
            row_dict['metadata'] = json.loads(row_dict['metadata'])

        return row_dict

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_evento_error", evento_id=evento_id, error=str(e))
        raise HTTPException(status_code=500, detail="Error al obtener evento")


@router.get("/stats/summary")
async def get_event_statistics(
    unidad_id: Optional[str] = None,
    days: int = Query(7, ge=1, le=90, description="Últimos N días"),
):
    """
    Obtener estadísticas de eventos.

    Retorna conteo por tipo de evento en el período especificado.
    """
    try:
        start_date = datetime.utcnow() - timedelta(days=days)

        if unidad_id:
            query = """
                SELECT
                    tipo,
                    COUNT(*) as count
                FROM evento
                WHERE unidad_id = $1 AND ts >= $2
                GROUP BY tipo
                ORDER BY count DESC
            """
            rows = await db.fetch_all(query, unidad_id, start_date)
        else:
            query = """
                SELECT
                    tipo,
                    COUNT(*) as count
                FROM evento
                WHERE ts >= $1
                GROUP BY tipo
                ORDER BY count DESC
            """
            rows = await db.fetch_all(query, start_date)

        return {
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": datetime.utcnow().isoformat(),
            "unidad_id": unidad_id,
            "statistics": [dict(row) for row in rows],
        }

    except Exception as e:
        logger.error("get_event_statistics_error", error=str(e))
        raise HTTPException(
            status_code=500, detail="Error al obtener estadísticas de eventos"
        )
