"""
Conexión y pool de conexiones a PostgreSQL usando asyncpg.
"""
import asyncpg
import structlog
from typing import Optional
from .config import settings

logger = structlog.get_logger()


class Database:
    """Administrador de conexiones a la base de datos"""

    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Crear pool de conexiones"""
        try:
            self.pool = await asyncpg.create_pool(
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                database=settings.DB_NAME,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                min_size=settings.DB_MIN_POOL_SIZE,
                max_size=settings.DB_MAX_POOL_SIZE,
                command_timeout=60,
            )
            logger.info(
                "database_connected",
                host=settings.DB_HOST,
                database=settings.DB_NAME,
                pool_size=f"{settings.DB_MIN_POOL_SIZE}-{settings.DB_MAX_POOL_SIZE}",
            )
        except Exception as e:
            logger.error("database_connection_failed", error=str(e))
            raise

    async def disconnect(self):
        """Cerrar pool de conexiones"""
        if self.pool:
            await self.pool.close()
            logger.info("database_disconnected")

    async def fetch_one(self, query: str, *args):
        """Ejecutar query y retornar un registro"""
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetch_all(self, query: str, *args):
        """Ejecutar query y retornar todos los registros"""
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def execute(self, query: str, *args):
        """Ejecutar query sin retornar datos"""
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def execute_many(self, query: str, args_list):
        """Ejecutar query múltiples veces con diferentes parámetros"""
        async with self.pool.acquire() as conn:
            return await conn.executemany(query, args_list)


# Instancia global de base de datos
db = Database()
