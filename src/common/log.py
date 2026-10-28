"""Logging estructurado en JSON.

Un log como `{"level": "ERROR", "bucket": "ventas-bronze", "msg": "..."}` se puede filtrar
y contar con herramientas (CloudWatch Logs Insights, grep + jq). Un texto libre como
"falló el bucket ventas-bronze" no se puede consultar igual.

Uso:
    log = get_logger(__name__)
    log.info("bucket creado", extra={"bucket": "ventas-bronze"})
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime

# Atributos que trae todo LogRecord. Cualquier otro atributo vino de `extra=` y lo incluimos.
_STANDARD_ATTRS = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime", "taskName"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        payload.update({k: v for k, v in record.__dict__.items() if k not in _STANDARD_ATTRS})
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: str = "INFO") -> None:
    """Configura el logger raíz una sola vez. Se puede llamar varias veces sin duplicar handlers."""
    root = logging.getLogger()
    root.setLevel(level)
    if not any(isinstance(h.formatter, JsonFormatter) for h in root.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        root.handlers = [handler]
    # boto3 es muy verboso en DEBUG; lo bajamos para que no tape nuestros logs.
    for noisy in ("botocore", "boto3", "urllib3", "s3transfer"):
        logging.getLogger(noisy).setLevel("WARNING")


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
