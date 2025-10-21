"""
API endpoints para gestión de rutas.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import structlog

from ..models.schemas import RutaCreate, RutaResponse, UnidadRutaAssignmentCreate
from ..core.database import db

logger = structlog.get_logger()
router = APIRouter(prefix="/rutas", tags=["Rutas"])


@router.get("", response_model=List[RutaResponse])
async def list_rutas(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """Listar todas las rutas"""
    try:
        rows = await db.fetch_all(
            """
            SELECT id, nombre, descripcion, distancia_m, created_at
            FROM ruta
            ORDER BY nombre
            LIMIT $1 OFFSET $2
            """,
            limit,
            offset,
        )
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error("list_rutas_error", error=str(e))
        raise HTTPException(status_code=500, detail="Error al listar rutas")


@router.get("/{ruta_id}", response_model=dict)
async def get_ruta(ruta_id: int):
    """
    Obtener detalles de una ruta incluyendo geometría.

    Retorna la geometría en formato GeoJSON.
    """
    try:
        row = await db.fetch_one(
            """
            SELECT
                id,
                nombre,
                descripcion,
                distancia_m,
                ST_AsGeoJSON(linea::geometry) as geojson,
                created_at,
                updated_at
            FROM ruta
            WHERE id = $1
            """,
            ruta_id,
        )

        if not row:
            raise HTTPException(status_code=404, detail="Ruta no encontrada")

        import json

        result = dict(row)
        result["geojson"] = json.loads(result["geojson"]) if result["geojson"] else None

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_ruta_error", ruta_id=ruta_id, error=str(e))
        raise HTTPException(status_code=500, detail="Error al obtener ruta")


@router.post("", response_model=RutaResponse, status_code=201)
async def create_ruta(ruta: RutaCreate):
    """
    Crear nueva ruta.

    Las coordenadas deben proporcionarse como una lista de tuplas [lon, lat].
    Ejemplo: [[- 98.2, 19.04], [-98.19, 19.045], [-98.18, 19.05]]
    """
    try:
        # Construir LineString desde coordenadas
        if len(ruta.coordinates) < 2:
            raise HTTPException(
                status_code=400,
                detail="Se requieren al menos 2 puntos para crear una ruta",
            )

        # Crear string de coordenadas para PostGIS
        coords_str = ", ".join([f"{lon} {lat}" for lon, lat in ruta.coordinates])
        linestring_wkt = f"LINESTRING({coords_str})"

        row = await db.fetch_one(
            """
            INSERT INTO ruta (nombre, descripcion, linea, distancia_m)
            VALUES (
                $1,
                $2,
                ST_GeogFromText($3),
                ST_Length(ST_GeogFromText($3))
            )
            RETURNING id, nombre, descripcion, distancia_m, created_at
            """,
            ruta.nombre,
            ruta.descripcion,
            f"SRID=4326;{linestring_wkt}",
        )

        logger.info("ruta_created", ruta_id=row["id"], nombre=ruta.nombre)
        return dict(row)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("create_ruta_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Error al crear ruta")


@router.delete("/{ruta_id}", status_code=204)
async def delete_ruta(ruta_id: int):
    """Eliminar ruta"""
    try:
        result = await db.execute("DELETE FROM ruta WHERE id = $1", ruta_id)

        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Ruta no encontrada")

        logger.info("ruta_deleted", ruta_id=ruta_id)
        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_ruta_error", ruta_id=ruta_id, error=str(e))
        raise HTTPException(status_code=500, detail="Error al eliminar ruta")


@router.post("/assignments", status_code=201)
async def assign_ruta_to_unidad(assignment: UnidadRutaAssignmentCreate):
    """
    Asignar ruta a una unidad.

    Si la unidad ya tiene una ruta asignada activa, se cerrará automáticamente.
    """
    try:
        # Cerrar asignación activa previa
        await db.execute(
            """
            UPDATE unidad_ruta_assignment
            SET end_ts = now()
            WHERE unidad_id = $1 AND end_ts IS NULL
            """,
            assignment.unidad_id,
        )

        # Crear nueva asignación
        row = await db.fetch_one(
            """
            INSERT INTO unidad_ruta_assignment (unidad_id, ruta_id, start_ts)
            VALUES ($1, $2, $3)
            RETURNING id, unidad_id, ruta_id, start_ts, end_ts, created_at
            """,
            assignment.unidad_id,
            assignment.ruta_id,
            assignment.start_ts,
        )

        logger.info(
            "ruta_assigned",
            unidad_id=assignment.unidad_id,
            ruta_id=assignment.ruta_id,
        )
        return dict(row)

    except Exception as e:
        logger.error("assign_ruta_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Error al asignar ruta")


@router.get("/assignments/{unidad_id}")
async def get_unidad_route_assignments(unidad_id: str):
    """Obtener historial de asignaciones de rutas de una unidad"""
    try:
        rows = await db.fetch_all(
            """
            SELECT
                a.id,
                a.unidad_id,
                a.ruta_id,
                r.nombre as ruta_nombre,
                a.start_ts,
                a.end_ts,
                a.created_at
            FROM unidad_ruta_assignment a
            INNER JOIN ruta r ON r.id = a.ruta_id
            WHERE a.unidad_id = $1
            ORDER BY a.start_ts DESC
            """,
            unidad_id,
        )
        return [dict(row) for row in rows]

    except Exception as e:
        logger.error("get_route_assignments_error", unidad_id=unidad_id, error=str(e))
        raise HTTPException(
            status_code=500, detail="Error al obtener asignaciones de rutas"
        )
