"""Configuración central, leída de variables de entorno.

Todo lo que cambia entre entornos (local, Docker, AWS) vive en variables de entorno y
no en el código. Así el mismo código corre en los tres lados y ningún secreto
termina en el repo.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

LAYERS: tuple[str, ...] = ("bronze", "silver", "gold")


class ConfigError(RuntimeError):
    """Falta o es inválida una variable de entorno."""


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigError(
            f"Falta la variable de entorno {name}. ¿Copiaste .env.example a .env y la completaste?"
        )
    return value


@dataclass(frozen=True)
class PostgresSettings:
    host: str
    port: int
    db: str
    user: str
    # repr=False: si alguien hace print(settings) o lo loguea, el password no aparece.
    password: str = field(repr=False)

    @property
    def conninfo(self) -> str:
        return (
            f"host={self.host} port={self.port} dbname={self.db} "
            f"user={self.user} password={self.password}"
        )


@dataclass(frozen=True)
class StorageSettings:
    # None significa "S3 real de AWS": boto3 resuelve el endpoint según la región.
    endpoint_url: str | None
    region: str
    bucket_prefix: str
    access_key: str | None = field(default=None, repr=False)
    secret_key: str | None = field(default=None, repr=False)

    def bucket_for(self, layer: str) -> str:
        if layer not in LAYERS:
            raise ValueError(f"Capa desconocida: {layer!r}. Válidas: {LAYERS}")
        return f"{self.bucket_prefix}-{layer}"

    @property
    def buckets(self) -> tuple[str, ...]:
        return tuple(self.bucket_for(layer) for layer in LAYERS)


@dataclass(frozen=True)
class Settings:
    postgres: PostgresSettings
    storage: StorageSettings
    log_level: str


def load_settings() -> Settings:
    """Lee y valida la configuración. Falla rápido y con un mensaje claro si falta algo."""
    port_raw = os.getenv("POSTGRES_PORT", "5432")
    try:
        port = int(port_raw)
    except ValueError as exc:
        raise ConfigError(f"POSTGRES_PORT debe ser un número, llegó {port_raw!r}") from exc

    endpoint = os.getenv("S3_ENDPOINT_URL", "").strip() or None
    storage = StorageSettings(
        endpoint_url=endpoint,
        region=os.getenv("AWS_REGION", "us-east-1"),
        bucket_prefix=_require("S3_BUCKET_PREFIX"),
        # En AWS no pasamos claves: boto3 toma las credenciales del rol IAM o del perfil local.
        # Las pedimos solo cuando hay un endpoint local (RustFS).
        access_key=_require("S3_ACCESS_KEY") if endpoint else None,
        secret_key=_require("S3_SECRET_KEY") if endpoint else None,
    )

    return Settings(
        postgres=PostgresSettings(
            host=_require("POSTGRES_HOST"),
            port=port,
            db=_require("POSTGRES_DB"),
            user=_require("POSTGRES_USER"),
            password=_require("POSTGRES_PASSWORD"),
        ),
        storage=storage,
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
    )
