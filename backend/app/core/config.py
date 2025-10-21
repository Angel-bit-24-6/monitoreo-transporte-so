"""
Configuración centralizada de la aplicación usando Pydantic Settings.
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Configuración de la aplicación"""

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/transporte_db"
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "transporte_db"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_MIN_POOL_SIZE: int = 10
    DB_MAX_POOL_SIZE: int = 50

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = False

    # Token - Configuración Detallada
    TOKEN_TTL_SECONDS: int = 600  # Testing: 600 (10 min) | Producción: 2592000 (30 días)
    TOKEN_RENEWAL_THRESHOLD_MINUTES: int = 7  # Testing: 7 min | Producción: 10080 min (7 días)
    TOKEN_GRACE_PERIOD_DAYS: int = 7
    CLEANUP_TOKEN_DAYS: int = 30
    TOKEN_RENEWAL_CHECK_INTERVAL_SECONDS: int = 60  # Testing: 60 (1 min) | Producción: 3600 (1 hora)

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_TIMEOUT: int = 300

    # Sistema Config
    OUT_OF_ROUTE_THRESHOLD_M: float = 200.0
    STOP_SPEED_THRESHOLD: float = 1.5
    STOP_TIME_THRESHOLD_S: int = 120

    class Config:
        env_file = ".env"
        case_sensitive = True


# Instancia global de configuración
settings = Settings()


# ==========================================
# FUNCIONES DE UTILIDAD PARA TOKENS
# ==========================================

def get_token_config_summary() -> dict:
    """Obtener resumen de configuración de tokens para logs"""
    return {
        "ttl_seconds": settings.TOKEN_TTL_SECONDS,
        "ttl_human": format_seconds(settings.TOKEN_TTL_SECONDS),
        "renewal_threshold_minutes": settings.TOKEN_RENEWAL_THRESHOLD_MINUTES,
        "renewal_threshold_human": format_minutes(settings.TOKEN_RENEWAL_THRESHOLD_MINUTES),
        "renewal_check_interval_seconds": settings.TOKEN_RENEWAL_CHECK_INTERVAL_SECONDS,
        "renewal_check_interval_human": format_seconds(settings.TOKEN_RENEWAL_CHECK_INTERVAL_SECONDS),
        "grace_period_days": settings.TOKEN_GRACE_PERIOD_DAYS,
        "mode": "TESTING" if settings.TOKEN_TTL_SECONDS < 86400 else "PRODUCCIÓN"
    }


def format_seconds(seconds: int) -> str:
    """Convertir segundos a formato legible"""
    if seconds < 3600:
        return f"{seconds // 60} minutos"
    elif seconds < 86400:
        return f"{seconds // 3600} horas"
    else:
        return f"{seconds // 86400} días"


def format_minutes(minutes: int) -> str:
    """Convertir minutos a formato legible"""
    if minutes < 60:
        return f"{minutes} minutos"
    elif minutes < 1440:
        return f"{minutes // 60} horas"
    else:
        return f"{minutes // 1440} días"


def validate_token_config():
    """Validar que la configuración sea coherente"""
    errors = []

    # TTL debe ser mayor que umbral de renovación
    ttl_minutes = settings.TOKEN_TTL_SECONDS / 60
    if ttl_minutes <= settings.TOKEN_RENEWAL_THRESHOLD_MINUTES:
        errors.append(
            f"ERROR: TTL ({ttl_minutes:.1f} min) debe ser mayor que "
            f"umbral de renovación ({settings.TOKEN_RENEWAL_THRESHOLD_MINUTES} min)"
        )

    # Umbral de renovación debe ser positivo
    if settings.TOKEN_RENEWAL_THRESHOLD_MINUTES <= 0:
        errors.append("ERROR: Umbral de renovación debe ser mayor que 0")

    # TTL debe ser al menos 1.5x el umbral (para que tenga sentido el grace period)
    if ttl_minutes < (settings.TOKEN_RENEWAL_THRESHOLD_MINUTES * 1.5):
        errors.append(
            f"ADVERTENCIA: TTL ({ttl_minutes:.1f} min) es muy cercano al umbral "
            f"({settings.TOKEN_RENEWAL_THRESHOLD_MINUTES} min). "
            f"Debería ser al menos 1.5x mayor."
        )

    return errors


# Validar configuración al importar
_validation_errors = validate_token_config()
if _validation_errors:
    for error in _validation_errors:
        print(f"⚠️ {error}")
