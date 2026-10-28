"""Cliente S3 único para todo el proyecto: el mismo código habla con RustFS (local) y AWS S3."""

from __future__ import annotations

import boto3
from botocore.client import BaseClient
from botocore.config import Config

from common.config import StorageSettings


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
