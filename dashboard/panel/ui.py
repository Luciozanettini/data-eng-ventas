"""Componentes visuales reutilizados por varias páginas."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import streamlit as st

from panel.meta import STATUS_ICON, STATUS_LABEL, MetaError, ProjectMeta, load_meta


def get_meta() -> ProjectMeta:
    """Carga project.yml; si tiene un error, lo muestra claro en vez de romper la página."""
    try:
        return load_meta()
    except (MetaError, OSError) as exc:
        st.error(f"No pude leer dashboard/project.yml: {exc}")
        st.stop()


def local_time(dt: datetime | None = None) -> datetime:
    """Convierte a la zona horaria de APP_TIMEZONE solo para MOSTRAR.

    Regla de oro: los datos se guardan siempre en UTC; la hora local es cosa de la pantalla.
    """
    tz = ZoneInfo(os.getenv("APP_TIMEZONE", "America/Argentina/Buenos_Aires"))
    return (dt or datetime.now(UTC)).astimezone(tz)


def status_text(status: str) -> str:
    return f"{STATUS_ICON[status]} {STATUS_LABEL[status]}"


def coming_soon(meta: ProjectMeta, stage_number: int, will_show: list[str]) -> None:
    """Sección que todavía no tiene datos: muestra en qué etapa llega y qué va a mostrar."""
    stage = meta.stage(stage_number)
    st.info(
        f"Esta sección se activa en la **Etapa {stage.number}: {stage.name}** "
        f"({status_text(stage.status)}).",
        icon="🚧",
    )
    st.markdown("**Lo que vas a ver acá:**")
    st.markdown("\n".join(f"- {item}" for item in will_show))
