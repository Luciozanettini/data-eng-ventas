import pandas as pd
import streamlit as st

from common.config import ConfigError, load_settings
from panel.env_status import bucket_stats, human_size, postgres_stats
from panel.ui import local_time

st.title("🗄️ Datos")
st.caption(
    "Estado real del entorno: cuántos archivos hay en cada capa del data lake y qué tablas "
    "hay en Postgres. Se actualiza cada 30 segundos o con el botón."
)

try:
    settings = load_settings()
except ConfigError as exc:
    st.error(f"Configuración incompleta: {exc}")
    st.stop()


# ttl=30: durante 30 s se reutiliza el resultado en vez de consultar en cada clic.
@st.cache_data(ttl=30, show_spinner="Consultando buckets…")
def _buckets():
    return bucket_stats(settings)


@st.cache_data(ttl=30, show_spinner="Consultando Postgres…")
def _postgres():
    return postgres_stats(settings)


if st.button("🔄 Actualizar ahora"):
    st.cache_data.clear()

st.caption(f"Consultado: {local_time():%H:%M:%S}")

st.subheader("Data lake (S3 local)")
try:
    buckets = _buckets()
    cols = st.columns(len(buckets))
    for col, b in zip(cols, buckets, strict=True):
        with col, st.container(border=True):
            st.markdown(f"**{b.layer.upper()}**  \n`{b.bucket}`")
            st.metric("Archivos", b.objects)
            st.caption(
                f"{human_size(b.size_bytes)} · última escritura: "
                + (f"{local_time(b.last_modified):%Y-%m-%d %H:%M}" if b.last_modified else "nunca")
            )
    if all(b.objects == 0 for b in buckets):
        st.info("Los buckets existen pero están vacíos: los datos llegan en la **Etapa 3**.")
except Exception as exc:  # el panel no debe romperse si un servicio está caído
    st.error(f"No pude leer los buckets: {exc}")
    st.caption("¿Está corriendo el entorno? Probá `docker compose up -d`.")

st.subheader("Warehouse (Postgres)")
try:
    pg = _postgres()
    st.success(f"Conectado · {pg.version}")
    if pg.tables:
        st.dataframe(
            pd.DataFrame(
                {"Esquema": t.schema, "Tabla": t.table, "Filas": t.rows} for t in pg.tables
            ),
            hide_index=True,
            width="stretch",
        )
    else:
        st.info("Todavía no hay tablas: las crea dbt en la **Etapa 4** (silver y gold).")
except Exception as exc:
    st.error(f"No pude conectar a Postgres: {exc}")
    st.caption("¿Está corriendo el entorno? Probá `docker compose up -d`.")
