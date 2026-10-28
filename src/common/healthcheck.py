"""Prueba de humo del entorno: verifica Postgres y el object storage, y crea los buckets.

Corre con:  python -m common.healthcheck
(En Docker lo ejecuta el servicio `init` de docker-compose).

Es *idempotente*: si la corrés 1 o 100 veces el resultado final es el mismo
(los buckets existen una sola vez y no hay errores por "ya existe").
"""

from __future__ import annotations

import sys
import time
from collections.abc import Callable

import boto3
import psycopg
from botocore.client import BaseClient
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from common.config import ConfigError, PostgresSettings, Settings, StorageSettings, load_settings
from common.log import configure_logging, get_logger

log = get_logger(__name__)


def with_retries[T](
    fn: Callable[[], T],
    *,
    what: str,
    attempts: int = 10,
    base_wait_s: float = 1.0,
    retry_on: tuple[type[Exception], ...] = (Exception,),
) -> T:
    """Reintenta `fn` con espera exponencial (1s, 2s, 4s... hasta 10s).

    Los servicios recién levantados tardan unos segundos en aceptar conexiones. Sin
    reintentos, el primer intento falla y el pipeline se cae por algo pasajero.
    """
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except retry_on as exc:
            if attempt == attempts:
                raise
            wait = min(base_wait_s * 2 ** (attempt - 1), 10.0)
            log.warning(
                "reintentando",
                extra={"what": what, "attempt": attempt, "wait_s": wait, "error": str(exc)},
            )
            time.sleep(wait)
    raise AssertionError("inalcanzable")


def check_postgres(pg: PostgresSettings) -> str:
    def _connect() -> str:
        with psycopg.connect(pg.conninfo, connect_timeout=3) as conn:
            row = conn.execute("select version()").fetchone()
            return row[0] if row else "desconocida"

    version = with_retries(_connect, what="postgres", retry_on=(psycopg.OperationalError,))
    log.info("postgres ok", extra={"host": pg.host, "db": pg.db, "version": version.split(",")[0]})
    return version


def make_s3_client(storage: StorageSettings) -> BaseClient:
    return boto3.client(
        "s3",
        endpoint_url=storage.endpoint_url,
        region_name=storage.region,
        aws_access_key_id=storage.access_key,
        aws_secret_access_key=storage.secret_key,
        # En local usamos "path style" (http://host:9000/bucket) porque no hay DNS por bucket.
        config=Config(s3={"addressing_style": "path"} if storage.endpoint_url else {}),
    )


def ensure_bucket(s3: BaseClient, bucket: str, region: str) -> bool:
    """Crea el bucket si no existe. Devuelve True si lo creó y False si ya estaba."""
    try:
        s3.head_bucket(Bucket=bucket)
        return False
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code not in ("404", "NoSuchBucket", "NotFound"):
            raise  # 403 u otro error: no es "no existe", es un problema real (permisos, etc.)

    kwargs: dict[str, object] = {"Bucket": bucket}
    # Particularidad de AWS: en us-east-1 NO se manda LocationConstraint; en otras regiones sí.
    if region != "us-east-1":
        kwargs["CreateBucketConfiguration"] = {"LocationConstraint": region}
    try:
        s3.create_bucket(**kwargs)
    except ClientError as exc:
        # Otro proceso pudo crearlo entre el head y el create: también es éxito.
        if exc.response.get("Error", {}).get("Code") != "BucketAlreadyOwnedByYou":
            raise
        return False
    return True


def check_storage(storage: StorageSettings) -> None:
    s3 = make_s3_client(storage)
    with_retries(s3.list_buckets, what="s3", retry_on=(BotoCoreError, ClientError))
    for bucket in storage.buckets:
        created = ensure_bucket(s3, bucket, storage.region)
        # Ojo: "created" es un campo reservado de LogRecord (logging lanza KeyError), por eso
        # usamos otro nombre. Ruff (regla G101) lo detecta antes de que explote en runtime.
        log.info("bucket ok", extra={"bucket": bucket, "was_created": created})


def run(settings: Settings) -> None:
    check_postgres(settings.postgres)
    check_storage(settings.storage)


def main() -> int:
    try:
        settings = load_settings()
    except ConfigError as exc:
        configure_logging()
        log.error("configuración inválida", extra={"error": str(exc)})
        return 1

    configure_logging(settings.log_level)
    try:
        run(settings)
    except Exception:
        # Último recurso: logueamos con el stacktrace y salimos con código != 0 para que
        # Docker/Airflow/CI se enteren de que falló (un "print" y salir con 0 lo ocultaría).
        log.exception("healthcheck falló")
        return 1
    log.info("entorno listo")
    return 0


if __name__ == "__main__":
    sys.exit(main())
