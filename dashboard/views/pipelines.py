import streamlit as st

from panel.ui import coming_soon, get_meta

st.title("⏱️ Pipelines")
coming_soon(
    get_meta(),
    5,
    [
        "Cada DAG de Airflow (`daily_sales_dag`, `backfill_dag`) con su última corrida.",
        "Resultado: ✅ éxito / ❌ falla, y cuánto tardó.",
        "Historial de corridas recientes, consultado a la API REST de Airflow.",
    ],
)
