import streamlit as st

from panel.ui import coming_soon, get_meta

st.title("✅ Calidad")
coming_soon(
    get_meta(),
    6,
    [
        "Resultados de los tests de dbt (únicos, no nulos, relaciones entre tablas).",
        "Reglas de `data_quality.yml`: cuáles pasaron, cuáles fallaron y por qué.",
        "Detalle de las filas que no cumplen una regla, para investigar.",
    ],
)
