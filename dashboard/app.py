"""Panel del proyecto: punto de entrada de Streamlit.

Corre con:  streamlit run dashboard/app.py   (en Docker lo hace el servicio `dashboard`)
Este archivo solo arma la navegación y la barra lateral; cada sección vive en views/.
"""

import streamlit as st

from panel.ui import get_meta, status_text

st.set_page_config(page_title="data-eng-ventas · Panel", page_icon="📊", layout="wide")

# url_path fijo: cada sección tiene una URL estable (http://localhost:8501/datos, etc.).
pages = {
    "Proyecto": [
        st.Page("views/mapa.py", title="Mapa del proyecto", icon="🗺️", default=True),
        st.Page("views/arquitectura.py", title="Arquitectura", icon="🏗️", url_path="arquitectura"),
        st.Page("views/diario.py", title="Diario de aprendizaje", icon="📓", url_path="diario"),
    ],
    "Operación": [
        st.Page("views/datos.py", title="Datos", icon="🗄️", url_path="datos"),
        st.Page("views/pipelines.py", title="Pipelines", icon="⏱️", url_path="pipelines"),
        st.Page("views/calidad.py", title="Calidad", icon="✅", url_path="calidad"),
        st.Page("views/infra.py", title="Infraestructura AWS", icon="☁️", url_path="infra"),
    ],
}
nav = st.navigation(pages)

meta = get_meta()
with st.sidebar:
    st.markdown("#### Etapas")
    for stage in meta.stages:
        st.markdown(f"{status_text(stage.status).split()[0]} **{stage.number}.** {stage.name}")
    done = sum(s.status == "listo" for s in meta.stages)
    st.progress(done / len(meta.stages), text=f"{done} de {len(meta.stages)} etapas listas")

nav.run()
