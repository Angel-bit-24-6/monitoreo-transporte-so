"""
API de Puntos de Interés (POIs).
Endpoints para consultar hospitales, farmacias, papelerías, etc.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
import structlog

from ..core.database import db

logger = structlog.get_logger()
router = APIRouter(prefix="/pois", tags=["POIs"])


# ============================================================================
# MODELOS PYDANTIC
# ============================================================================

class POIResponse(BaseModel):
    """Modelo de respuesta para un POI"""
    id: int
    nombre: str
    categoria: str
    direccion: Optional[str]
    telefono: Optional[str]
    horario: Optional[str]
    lat: float
    lon: float
    distancia_m: Optional[float] = None  # Opcional, solo cuando se busca por cercanía

    class Config:
        from_attributes = True


class POICategoriaStats(BaseModel):
    """Estadísticas de POIs por categoría"""
    categoria: str
    total: int


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("", response_model=List[POIResponse])
async def listar_pois(
    categoria: Optional[str] = Query(None, description="Filtrar por categoría (hospital, farmacia, papeleria, gasolinera, banco)"),
    activo: bool = Query(True, description="Filtrar solo POIs activos")
):
    """
    Listar todos los POIs.

    - **categoria**: Filtrar por categoría específica
    - **activo**: Solo POIs activos (default: true)
    """
    try:
        if categoria:
            query = """
                SELECT
                    id,
                    nombre,
                    categoria,
                    direccion,
                    telefono,
                    horario,
                    ST_Y(ubicacion::geometry) AS lat,
                    ST_X(ubicacion::geometry) AS lon
                FROM poi
                WHERE activo = $1 AND categoria = $2
                ORDER BY categoria, nombre
            """
            rows = await db.fetch_all(query, activo, categoria)
        else:
            query = """
                SELECT
                    id,
                    nombre,
                    categoria,
                    direccion,
                    telefono,
                    horario,
                    ST_Y(ubicacion::geometry) AS lat,
                    ST_X(ubicacion::geometry) AS lon
                FROM poi
                WHERE activo = $1
                ORDER BY categoria, nombre
            """
            rows = await db.fetch_all(query, activo)

        return [dict(row) for row in rows]
    except Exception as e:
        logger.error("listar_pois_error", error=str(e))
        raise HTTPException(status_code=500, detail="Error al listar POIs")


@router.get("/cercanos", response_model=List[POIResponse])
async def pois_cercanos(
    lat: float = Query(..., description="Latitud del punto de referencia"),
    lon: float = Query(..., description="Longitud del punto de referencia"),
    radio: int = Query(1000, description="Radio de búsqueda en metros (default: 1000m)"),
    categoria: Optional[str] = Query(None, description="Filtrar por categoría"),
    limit: int = Query(10, ge=1, le=50, description="Número máximo de resultados")
):
    """
    Buscar POIs cercanos a una coordenada.

    - **lat**: Latitud del punto de referencia
    - **lon**: Longitud del punto de referencia
    - **radio**: Radio de búsqueda en metros (default: 1000m)
    - **categoria**: Filtrar por categoría (opcional)
    - **limit**: Máximo de resultados (default: 10)

    Los resultados se ordenan por distancia (más cercanos primero).
    """
    try:
        if categoria:
            query = """
                SELECT
                    id,
                    nombre,
                    categoria,
                    direccion,
                    telefono,
                    horario,
                    ST_Y(ubicacion::geometry) AS lat,
                    ST_X(ubicacion::geometry) AS lon,
                    ROUND(ST_Distance(
                        ubicacion,
                        ST_GeogFromText('SRID=4326;POINT(' || $2 || ' ' || $1 || ')')
                    )::numeric, 2) AS distancia_m
                FROM poi
                WHERE activo = TRUE
                  AND ST_DWithin(
                      ubicacion,
                      ST_GeogFromText('SRID=4326;POINT(' || $2 || ' ' || $1 || ')'),
                      $3
                  )
                  AND categoria = $4
                ORDER BY distancia_m
                LIMIT $5
            """
            rows = await db.fetch_all(query, lat, lon, radio, categoria, limit)
        else:
            query = """
                SELECT
                    id,
                    nombre,
                    categoria,
                    direccion,
                    telefono,
                    horario,
                    ST_Y(ubicacion::geometry) AS lat,
                    ST_X(ubicacion::geometry) AS lon,
                    ROUND(ST_Distance(
                        ubicacion,
                        ST_GeogFromText('SRID=4326;POINT(' || $2 || ' ' || $1 || ')')
                    )::numeric, 2) AS distancia_m
                FROM poi
                WHERE activo = TRUE
                  AND ST_DWithin(
                      ubicacion,
                      ST_GeogFromText('SRID=4326;POINT(' || $2 || ' ' || $1 || ')'),
                      $3
                  )
                ORDER BY distancia_m
                LIMIT $4
            """
            rows = await db.fetch_all(query, lat, lon, radio, limit)

        return [dict(row) for row in rows]
    except Exception as e:
        logger.error("pois_cercanos_error", error=str(e))
        raise HTTPException(status_code=500, detail="Error al buscar POIs cercanos")


@router.get("/buscar", response_model=List[POIResponse])
async def buscar_pois(
    q: str = Query(..., min_length=2, description="Término de búsqueda (nombre del POI)"),
    categoria: Optional[str] = Query(None, description="Filtrar por categoría"),
    limit: int = Query(20, ge=1, le=50, description="Número máximo de resultados")
):
    """
    Buscar POIs por nombre.

    - **q**: Término de búsqueda (mínimo 2 caracteres)
    - **categoria**: Filtrar por categoría (opcional)
    - **limit**: Máximo de resultados (default: 20)

    Búsqueda case-insensitive en el nombre del POI.
    """
    try:
        search_pattern = f"%{q}%"

        if categoria:
            query = """
                SELECT
                    id,
                    nombre,
                    categoria,
                    direccion,
                    telefono,
                    horario,
                    ST_Y(ubicacion::geometry) AS lat,
                    ST_X(ubicacion::geometry) AS lon
                FROM poi
                WHERE activo = TRUE
                  AND LOWER(nombre) LIKE LOWER($1)
                  AND categoria = $2
                ORDER BY nombre
                LIMIT $3
            """
            rows = await db.fetch_all(query, search_pattern, categoria, limit)
        else:
            query = """
                SELECT
                    id,
                    nombre,
                    categoria,
                    direccion,
                    telefono,
                    horario,
                    ST_Y(ubicacion::geometry) AS lat,
                    ST_X(ubicacion::geometry) AS lon
                FROM poi
                WHERE activo = TRUE
                  AND LOWER(nombre) LIKE LOWER($1)
                ORDER BY nombre
                LIMIT $2
            """
            rows = await db.fetch_all(query, search_pattern, limit)

        return [dict(row) for row in rows]
    except Exception as e:
        logger.error("buscar_pois_error", error=str(e))
        raise HTTPException(status_code=500, detail="Error al buscar POIs")


@router.get("/categorias", response_model=List[POICategoriaStats])
async def listar_categorias():
    """
    Obtener lista de categorías con conteo de POIs.

    Retorna todas las categorías disponibles y cuántos POIs activos hay en cada una.
    """
    try:
        query = """
            SELECT
                categoria,
                COUNT(*) AS total
            FROM poi
            WHERE activo = TRUE
            GROUP BY categoria
            ORDER BY categoria
        """
        rows = await db.fetch_all(query)
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error("listar_categorias_error", error=str(e))
        raise HTTPException(status_code=500, detail="Error al listar categorías")


@router.get("/{poi_id}", response_model=POIResponse)
async def obtener_poi(poi_id: int):
    """
    Obtener detalles de un POI específico por ID.

    - **poi_id**: ID del POI a consultar
    """
    try:
        query = """
            SELECT
                id,
                nombre,
                categoria,
                direccion,
                telefono,
                horario,
                ST_Y(ubicacion::geometry) AS lat,
                ST_X(ubicacion::geometry) AS lon
            FROM poi
            WHERE id = $1 AND activo = TRUE
        """
        row = await db.fetch_one(query, poi_id)

        if not row:
            raise HTTPException(status_code=404, detail=f"POI con ID {poi_id} no encontrado")

        return dict(row)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("obtener_poi_error", poi_id=poi_id, error=str(e))
        raise HTTPException(status_code=500, detail="Error al obtener POI")
