import streamlit as st

from panel.ui import coming_soon, get_meta

st.title("☁️ Infraestructura AWS")
coming_soon(
    get_meta(),
    7,
    [
        "Recursos definidos en Terraform: buckets S3, Glue Data Catalog, Athena, IAM.",
        "Resumen del último `terraform plan`: qué se crea, cambia o destruye.",
        "Costo mensual estimado y qué entra en el Free Tier.",
    ],
)
st.warning(
    "Nada de esta sección crea recursos reales. Cualquier `terraform apply` se hace solo "
    "con tu confirmación explícita, después de revisar el plan y el costo.",
    icon="🔒",
)
