import pandas as pd
import streamlit as st

from panel.ui import get_meta

meta = get_meta()

st.title("📓 Diario de aprendizaje")
st.caption("Qué construimos en cada etapa, qué decidimos y por qué, y qué quedó pendiente.")

tab_diario, tab_sugerencias = st.tabs(["Bitácora", "Sugerencias"])

with tab_diario:
    # La más reciente arriba y abierta; las anteriores, cerradas.
    for i, entry in enumerate(reversed(meta.diary)):
        with st.expander(f"Etapa {entry.stage}: {entry.title} · {entry.date}", expanded=i == 0):
            built, decisions, learned = st.columns(3)
            for col, title, items in (
                (built, "🔨 Qué construimos", entry.built),
                (decisions, "🧭 Decisiones", entry.decisions),
                (learned, "💡 Qué aprendimos", entry.learned),
            ):
                col.markdown(f"**{title}**")
                col.markdown("\n".join(f"- {item}" for item in items) or "-")

with tab_sugerencias:
    icon = {"pendiente": "⏳", "hecha": "✅", "descartada": "🚫"}
    estados = st.multiselect(
        "Estado", list(icon), default=["pendiente"], format_func=lambda s: f"{icon[s]} {s}"
    )
    rows = [s for s in meta.suggestions if s.status in estados]
    if rows:
        st.dataframe(
            pd.DataFrame(
                {
                    "Sugerencia": s.title,
                    "Etapa": s.stage,
                    "Esfuerzo": s.effort,
                    "Beneficio": s.benefit,
                    "Estado": f"{icon[s.status]} {s.status}",
                }
                for s in rows
            ),
            hide_index=True,
            width="stretch",
        )
    else:
        st.info("No hay sugerencias con ese estado.")
