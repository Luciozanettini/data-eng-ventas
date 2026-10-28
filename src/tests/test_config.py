import json
import logging

import pytest

from common.config import ConfigError, load_settings
from common.log import JsonFormatter

BASE_ENV = {
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": "5432",
    "POSTGRES_DB": "ventas",
    "POSTGRES_USER": "ventas",
    "POSTGRES_PASSWORD": "super-secreto",
    "S3_ENDPOINT_URL": "http://localhost:9000",
    "S3_ACCESS_KEY": "clave",
    "S3_SECRET_KEY": "otro-secreto",
    "S3_BUCKET_PREFIX": "ventas",
}


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    for key, value in BASE_ENV.items():
        monkeypatch.setenv(key, value)
    return monkeypatch


def test_buckets_por_capa(env: pytest.MonkeyPatch) -> None:
    settings = load_settings()
    assert settings.storage.buckets == ("ventas-bronze", "ventas-silver", "ventas-gold")


def test_capa_invalida_falla(env: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValueError, match="Capa desconocida"):
        load_settings().storage.bucket_for("platinum")


def test_falta_variable_da_mensaje_claro(env: pytest.MonkeyPatch) -> None:
    env.delenv("POSTGRES_PASSWORD")
    with pytest.raises(ConfigError, match="POSTGRES_PASSWORD"):
        load_settings()


def test_puerto_no_numerico(env: pytest.MonkeyPatch) -> None:
    env.setenv("POSTGRES_PORT", "abc")
    with pytest.raises(ConfigError, match="POSTGRES_PORT"):
        load_settings()


def test_secretos_no_aparecen_en_repr(env: pytest.MonkeyPatch) -> None:
    # Si alguien loguea la config por error, los passwords no deben filtrarse.
    text = repr(load_settings())
    assert "super-secreto" not in text
    assert "otro-secreto" not in text


def test_sin_endpoint_no_pide_claves(env: pytest.MonkeyPatch) -> None:
    # Modo AWS: sin endpoint local, las credenciales salen del rol IAM, no del .env.
    env.delenv("S3_ENDPOINT_URL")
    env.delenv("S3_ACCESS_KEY")
    env.delenv("S3_SECRET_KEY")
    storage = load_settings().storage
    assert storage.endpoint_url is None
    assert storage.access_key is None


def test_log_json_incluye_extra() -> None:
    record = logging.makeLogRecord(
        {"name": "t", "levelname": "INFO", "msg": "bucket ok", "bucket": "ventas-bronze"}
    )
    payload = json.loads(JsonFormatter().format(record))
    assert payload["msg"] == "bucket ok"
    assert payload["bucket"] == "ventas-bronze"
