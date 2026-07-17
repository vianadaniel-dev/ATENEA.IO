"""Carga y centralizacion de la configuracion de la aplicacion.

Toda la configuracion se lee desde el archivo .env. Ningun otro modulo debe
llamar a os.getenv() directamente: siempre debe importar desde aqui.
"""

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

# Carga las variables de entorno del archivo .env ubicado junto a este modulo.
load_dotenv()


class ConfigError(RuntimeError):
    """Se lanza cuando falta una variable de entorno obligatoria."""


def _require(nombre: str) -> str:
    valor = os.getenv(nombre)
    if not valor:
        raise ConfigError(
            f"Falta la variable de entorno obligatoria '{nombre}'. "
            "Definela en el archivo .env antes de iniciar la aplicacion."
        )
    return valor


def _get_int(nombre: str, por_defecto: int) -> int:
    valor = os.getenv(nombre)
    if valor is None or valor.strip() == "":
        return por_defecto
    try:
        return int(valor)
    except ValueError as exc:
        raise ConfigError(
            f"La variable '{nombre}' debe ser un numero entero, se recibio: {valor!r}"
        ) from exc


@dataclass(frozen=True)
class Settings:
    """Configuracion inmutable de la aplicacion."""

    # --- Base de datos (Supabase / PostgreSQL) ---
    DATABASE_URL: str = field(default_factory=lambda: _require("DATABASE_URL"))
    # Supabase exige TLS. Usar 'disable' solo para un PostgreSQL local.
    DB_SSLMODE: str = field(default_factory=lambda: os.getenv("DB_SSLMODE", "require"))
    DB_POOL_MIN: int = field(default_factory=lambda: _get_int("DB_POOL_MIN", 1))
    DB_POOL_MAX: int = field(default_factory=lambda: _get_int("DB_POOL_MAX", 10))
    DB_CONNECT_TIMEOUT: int = field(default_factory=lambda: _get_int("DB_CONNECT_TIMEOUT", 10))

    # --- Seguridad / JWT ---
    SECRET_KEY: str = field(default_factory=lambda: _require("SECRET_KEY"))
    ALGORITHM: str = field(default_factory=lambda: os.getenv("ALGORITHM", "HS256"))
    ACCESS_TOKEN_EXPIRE_MINUTES: int = field(
        default_factory=lambda: _get_int("ACCESS_TOKEN_EXPIRE_MINUTES", 60)
    )

    # --- Paginacion ---
    DEFAULT_PAGE_SIZE: int = field(default_factory=lambda: _get_int("DEFAULT_PAGE_SIZE", 20))
    MAX_PAGE_SIZE: int = field(default_factory=lambda: _get_int("MAX_PAGE_SIZE", 100))


settings = Settings()

# Alias a nivel de modulo por compatibilidad con los imports existentes.
DATABASE_URL = settings.DATABASE_URL
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
