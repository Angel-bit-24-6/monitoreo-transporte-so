"""
API endpoints para gestión de unidades.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import structlog

from ..models.schemas import (
    UnidadCreate,
    UnidadResponse,
    PosicionResponse,
)
from ..core.database import db

logger = structlog.get_logger()
router = APIRouter(prefix="/unidades", tags=["Unidades"])


@router.get("", response_model=List[UnidadResponse])
async def list_unidades(
    activo: Optional[bool] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """Listar todas las unidades"""
    try:
        if activo is not None:
            query = """
                SELECT id, placa, chofer, activo, created_at, updated_at
                FROM unidad
                WHERE activo = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
            """
            rows = await db.fetch_all(query, activo, limit, offset)
        else:
            query = """
                SELECT id, placa, chofer, activo, created_at, updated_at
                FROM unidad
                ORDER BY created_at DESC
                LIMIT $1 OFFSET $2
            """
            rows = await db.fetch_all(query, limit, offset)

        return [dict(row) for row in rows]
    except Exception as e:
        logger.error("list_unidades_error", error=str(e))
        raise HTTPException(status_code=500, detail="Error al listar unidades")


@router.get("/{unidad_id}", response_model=UnidadResponse)
async def get_unidad(unidad_id: str):
    """Obtener detalles de una unidad"""
    try:
        row = await db.fetch_one(
            """
            SELECT id, placa, chofer, activo, created_at, updated_at
            FROM unidad
            WHERE id = $1
            """,
            unidad_id,
        )

        if not row:
            raise HTTPException(status_code=404, detail="Unidad no encontrada")

        return dict(row)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_unidad_error", unidad_id=unidad_id, error=str(e))
        raise HTTPException(status_code=500, detail="Error al obtener unidad")


@router.post("", response_model=UnidadResponse, status_code=201)
async def create_unidad(unidad: UnidadCreate):
    """Crear nueva unidad"""
    try:
        # Verificar si ya existe
        existing = await db.fetch_one("SELECT id FROM unidad WHERE id = $1", unidad.id)
        if existing:
            raise HTTPException(
                status_code=409, detail=f"Unidad {unidad.id} ya existe"
            )

        # Insertar
        row = await db.fetch_one(
            """
            INSERT INTO unidad (id, placa, chofer, activo)
            VALUES ($1, $2, $3, $4)
            RETURNING id, placa, chofer, activo, created_at, updated_at
            """,
            unidad.id,
            unidad.placa,
            unidad.chofer,
            unidad.activo,
        )

        logger.info("unidad_created", unidad_id=unidad.id)
        return dict(row)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("create_unidad_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Error al crear unidad")


@router.patch("/{unidad_id}", response_model=UnidadResponse)
async def update_unidad(
    unidad_id: str,
    placa: Optional[str] = None,
    chofer: Optional[str] = None,
    activo: Optional[bool] = None,
):
    """Actualizar unidad existente"""
    try:
        # Verificar que existe
        existing = await db.fetch_one("SELECT id FROM unidad WHERE id = $1", unidad_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Unidad no encontrada")

        # Construir query dinámico
        updates = []
        params = []
        param_idx = 1

        if placa is not None:
            updates.append(f"placa = ${param_idx}")
            params.append(placa)
            param_idx += 1

        if chofer is not None:
            updates.append(f"chofer = ${param_idx}")
            params.append(chofer)
            param_idx += 1

        if activo is not None:
            updates.append(f"activo = ${param_idx}")
            params.append(activo)
            param_idx += 1

        if not updates:
            raise HTTPException(status_code=400, detail="No se proporcionaron campos para actualizar")

        updates.append(f"updated_at = now()")
        params.append(unidad_id)

        query = f"""
            UPDATE unidad
            SET {', '.join(updates)}
            WHERE id = ${param_idx}
            RETURNING id, placa, chofer, activo, created_at, updated_at
        """

        row = await db.fetch_one(query, *params)
        logger.info("unidad_updated", unidad_id=unidad_id)
        return dict(row)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("update_unidad_error", unidad_id=unidad_id, error=str(e))
        raise HTTPException(status_code=500, detail="Error al actualizar unidad")


@router.delete("/{unidad_id}", status_code=204)
async def delete_unidad(unidad_id: str):
    """Eliminar unidad"""
    try:
        result = await db.execute("DELETE FROM unidad WHERE id = $1", unidad_id)

        # Verificar si se eliminó algo
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Unidad no encontrada")

        logger.info("unidad_deleted", unidad_id=unidad_id)
        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_unidad_error", unidad_id=unidad_id, error=str(e))
        raise HTTPException(status_code=500, detail="Error al eliminar unidad")


@router.get("/{unidad_id}/posiciones", response_model=List[PosicionResponse])
async def get_unidad_positions(
    unidad_id: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """Obtener posiciones históricas de una unidad"""
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
        logger.error("get_unidad_positions_error", unidad_id=unidad_id, error=str(e))
        raise HTTPException(
            status_code=500, detail="Error al obtener posiciones de unidad"
        )
