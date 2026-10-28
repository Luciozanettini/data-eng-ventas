import streamlit as st

from panel.diagram import build_dot
from panel.ui import get_meta, status_text

meta = get_meta()

st.title("🏗️ Arquitectura")
st.caption(
    "Cómo viajan los datos: de las fuentes a la ingesta, por las capas bronze → silver → gold, "
    "hasta el consumo. Se va completando a medida que construimos."
)

# width="content": tamaño natural. Con "stretch" un diagrama ancho y bajo queda diminuto.
st.graphviz_chart(build_dot(meta.arch_nodes, meta.arch_edges), width="content")
st.markdown(
    f"{status_text('listo')} · {status_text('en_construccion')} · "
    f"{status_text('pendiente')} (borde punteado)  \n"
    "**→ línea llena:** los datos fluyen · **⇢ línea punteada violeta:** "
    "orquesta o valida (no mueve datos)"
)

st.divider()
st.subheader("Las capas, con un ejemplo")
st.markdown(
    "Seguimos **una misma venta** a través de las capas. Cada capa tiene un trabajo y "
    "nunca se pisa la anterior: si algo sale mal, se reprocesa desde atrás."
)

bronze, silver, gold = st.columns(3)
with bronze, st.container(border=True):
    st.markdown("#### 🥉 Bronze: crudo")
    st.markdown("Se guarda **tal cual llegó**, aunque venga sucio. Es tu respaldo.")
    st.code(
        '{"order_id": "A-17", "amount": "1.250,50",\n'
        ' "ts": "15/10/2026 21:03", "qty": "2"}\n'
        '{"order_id": "A-17", ...}  ← duplicado',
        language="json",
    )
with silver, st.container(border=True):
    st.markdown("#### 🥈 Silver: limpio")
    st.markdown("Tipos correctos, fechas en un único formato, **sin duplicados**.")
    st.code(
        "order_id | amount  | ordered_at          | qty\n"
        "A-17     | 1250.50 | 2026-10-15 21:03:00 | 2",
        language=None,
    )
with gold, st.container(border=True):
    st.markdown("#### 🥇 Gold: negocio")
    st.markdown("Listo para responder preguntas: **¿cuánto vendimos por día?**")
    st.code(
        "day        | orders | revenue\n2026-10-15 | 142    | 98,410.75",
        language=None,
    )

st.divider()
st.subheader("Qué pieza se construye en qué etapa")
for node in sorted(meta.arch_nodes, key=lambda n: n.stage):
    st.markdown(
        f"- {status_text(node.status).split()[0]} **{node.label}**: {node.detail} "
        f"*(etapa {node.stage})*"
    )
