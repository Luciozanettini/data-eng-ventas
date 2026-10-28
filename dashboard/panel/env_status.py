"""Consulta el estado real del entorno: tablas en Postgres y archivos en los buckets.

Solo lectura: el panel nunca modifica datos.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import psycopg
from psycopg import sql

from common.config import LAYERS, Settings
from common.s3 import make_s3_client


@dataclass(frozen=True)
class TableStats:
    schema: str
    table: str
    rows: int


@dataclass(frozen=True)
class PostgresStats:
    version: str
    tables: tuple[TableStats, ...]


@dataclass(frozen=True)
class BucketStats:
    layer: str
    bucket: str
    objects: int
    size_bytes: int
    last_modified: datetime | None


def postgres_stats(settings: Settings) -> PostgresStats:
    with psycopg.connect(settings.postgres.conninfo, connect_timeout=3) as conn:
        version_row = conn.execute("select version()").fetchone()
        tables = conn.execute(
            """
            select table_schema, table_name
            from information_schema.tables
            where table_schema not in ('pg_catalog', 'information_schema')
              and table_type = 'BASE TABLE'
            order by 1, 2
            """
        ).fetchall()
        stats = []
        for schema, table in tables:
            # sql.Identifier escapa los nombres: nunca armar SQL con f-strings (inyección SQL).
            query = sql.SQL("select count(*) from {}.{}").format(
                sql.Identifier(schema), sql.Identifier(table)
            )
            row = conn.execute(query).fetchone()
            stats.append(TableStats(schema, table, int(row[0]) if row else 0))
    version = version_row[0].split(",")[0] if version_row else "desconocida"
    return PostgresStats(version, tuple(stats))


def bucket_stats(settings: Settings) -> tuple[BucketStats, ...]:
    s3 = make_s3_client(settings.storage)
    paginator = s3.get_paginator("list_objects_v2")
    result = []
    for layer in LAYERS:
        bucket = settings.storage.bucket_for(layer)
        objects, size, last = 0, 0, None
        # El paginador pide de a 1000 objetos: sin él, solo veríamos los primeros 1000.
        for page in paginator.paginate(Bucket=bucket):
            for obj in page.get("Contents", []):
                objects += 1
                size += obj["Size"]
                modified = obj["LastModified"]
                last = modified if last is None or modified > last else last
        result.append(BucketStats(layer, bucket, objects, size, last))
    return tuple(result)


def human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"
