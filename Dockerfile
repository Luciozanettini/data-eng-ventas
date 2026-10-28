# Imagen de las piezas Python propias del proyecto (healthcheck, ingesta y,
# en la etapa 2, el panel). Airflow tendrá su propia imagen en la etapa 5.
FROM python:3.12-slim

# No generar .pyc y mostrar los logs al instante (sin buffer) en `docker compose logs`.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Copiamos primero solo lo necesario para instalar dependencias. Si después cambia
# el código pero no pyproject.toml, Docker reutiliza esta capa y el build es mucho más rápido.
COPY pyproject.toml README.md ./
COPY src ./src
COPY dashboard ./dashboard
# Instalación "editable" con el extra del panel. En docker-compose montamos el repo
# encima, y los cambios que hagas en tu PC se ven sin reconstruir la imagen.
RUN pip install -e ".[dashboard]"

# Correr como usuario sin privilegios: si alguien explota la app, no es root.
RUN useradd --create-home --uid 1000 app
USER app

CMD ["python", "-m", "common.healthcheck"]
