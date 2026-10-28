import pandas as pd
import streamlit as st

from panel.meta import STATUS_ICON, STATUSES, missing_ready_paths, repo_root
from panel.ui import get_meta, status_text

meta = get_meta()
root = repo_root()

st.title("🗺️ Mapa del proyecto")
st.caption(
    "Cada carpeta y archivo de la estructura objetivo: para qué sirve, en qué etapa se "
    "construye y en qué estado está. Se edita en `dashboard/project.yml`."
)

counts = meta.status_counts()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Avance del mapa", f"{meta.progress():.0%}")
c2.metric(status_text("listo"), counts["listo"])
c3.metric(status_text("en_construccion"), counts["en_construccion"])
c4.metric(status_text("pendiente"), counts["pendiente"])

missing = missing_ready_paths(meta, root)
if missing:
    st.warning(
        "Marcado como listo en project.yml pero no existe en el repo: "
        + ", ".join(f"`{p}`" for p in missing)
    )

shown = st.multiselect(
    "Mostrar estados",
    STATUSES,
    default=list(STATUSES),
    format_func=status_text,
)
visible = [n for n in meta.nodes if n.status in shown]

tree_col, detail_col = st.columns([3, 2], gap="large")

with tree_col:
    lines = ["data-eng-ventas/"]
    for node in visible:
        lines.append(f"{'│   ' * node.depth}├── {STATUS_ICON[node.status]} {node.name}")
    st.code("\n".join(lines), language=None)

with detail_col:
    if not visible:
        st.info("No hay elementos con esos estados.")
    else:
        node = st.selectbox(
            "Elegí un archivo o carpeta",
            visible,
            format_func=lambda n: f"{STATUS_ICON[n.status]} {n.path}",
        )
        stage = meta.stage(node.stage)
        exists = (root / node.path).exists()
        with st.container(border=True):
            st.markdown(f"### `{node.path}`")
            st.markdown(
                f"**Estado:** {status_text(node.status)}  \n**Etapa:** {stage.number}: {stage.name}"
            )
            st.write(node.description)
            st.caption("✔ Existe en el repo" if exists else "Todavía no existe en el repo")

with st.expander("Ver como tabla"):
    df = pd.DataFrame(
        {
            "Ruta": n.path,
            "Estado": status_text(n.status),
            "Etapa": n.stage,
            "Descripción": n.description,
        }
        for n in visible
    )
    st.dataframe(df, hide_index=True, width="stretch")
