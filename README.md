# data-eng-ventas

Proyecto personal de **ingeniería de datos**: un pipeline de ventas de una tienda online ficticia,
construido por capas (bronze → silver → gold). Corre completo en local con Docker y se despliega
en AWS con Terraform.

> Proyecto de aprendizaje, construido etapa por etapa. Cada etapa deja algo funcionando.

## Arquitectura (objetivo)

```
Fuentes ──► Ingesta ──► BRONZE ──► SILVER ──► GOLD ──► Consumo
(API /       (Python)    (crudo,    (limpio,   (métricas   (panel,
 eventos)                S3)        tipado)    de negocio)  Athena)
                         └──── orquestado por Airflow, testeado con dbt + pytest ────┘
```

| Pieza | Local (gratis) | AWS |
|---|---|---|
| Data lake (archivos) | RustFS (compatible S3) | S3 |
| Warehouse / consultas | Postgres | Glue Data Catalog + Athena |
| Transformaciones | dbt-postgres | dbt-athena |
| Orquestación | Airflow (Docker) | Airflow local o MWAA/alternativa (a evaluar) |
| Infraestructura | docker-compose | Terraform |

## Estado de las etapas

| # | Etapa | Estado |
|---|---|---|
| 0 | Preparar la PC (WSL2 + Docker) | ✅ listo |
| 1 | Base del repo + entorno Docker | ✅ listo |
| 2 | Panel visual (Streamlit) | ✅ listo |
| 3 | Ingesta (bronze) | ⏳ pendiente |
| 4 | Transformaciones con dbt (silver/gold) | ⏳ pendiente |
| 5 | Orquestación con Airflow | ⏳ pendiente |
| 6 | Tests y calidad de datos | ⏳ pendiente |
| 7 | Infraestructura AWS con Terraform | ⏳ pendiente |
| 8 | CI/CD con GitHub Actions | ⏳ pendiente |

## Cómo levantarlo

Requisitos: Docker Desktop y Python 3.12+ (opcional, para correr tests fuera de Docker).

```bash
# 1. Crear tu archivo de configuración local (no se sube a git)
cp .env.example .env        # y completá los passwords

# 2. Levantar el entorno
docker compose up -d --build

# 3. Ver que la prueba de humo terminó bien ("entorno listo")
docker compose logs init
```

| Servicio | URL / conexión | Para qué |
|---|---|---|
| **Panel del proyecto** | http://localhost:8501 | Mapa, arquitectura, datos y diario de aprendizaje |
| Consola de RustFS (S3 local) | http://localhost:9001 | Ver buckets y archivos (usuario/clave: `S3_ACCESS_KEY` / `S3_SECRET_KEY` de tu `.env`) |
| API S3 local | http://localhost:9000 | La usa boto3 |
| Postgres | `localhost:5432` | Warehouse local |

Todos los puertos se publican solo en `127.0.0.1`: se acceden desde tu PC, no desde otras
máquinas de tu red.

Apagar: `docker compose down` (conserva datos) · Borrar todo: `docker compose down -v`.

### El panel

El panel se actualiza solo: si editás un archivo de `dashboard/`, a los pocos segundos se recarga.
Para cambiar estados del mapa, la arquitectura o el diario, se edita **`dashboard/project.yml`**:
no hace falta tocar código Python. Un test (`test_project_meta.py`) avisa si algo marcado como
"listo" no existe en el repo.

### Desarrollo y tests (fuera de Docker)

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows (en Linux/Mac: source .venv/bin/activate)
pip install -e ".[dev]"
ruff check . && ruff format --check .
pytest
```

## Estructura

```
.
├── docker-compose.yml   # entorno local: postgres + s3 (RustFS) + init
├── Dockerfile           # imagen de nuestro código Python
├── pyproject.toml       # dependencias y configuración de ruff/pytest
├── dashboard/           # panel Streamlit: http://localhost:8501
│   ├── app.py           # navegación y barra lateral
│   ├── project.yml      # fuente de verdad: etapas, mapa, arquitectura, diario
│   ├── panel/           # lógica testeable (leer project.yml, diagrama, consultas)
│   └── views/           # una página por sección
├── src/
│   ├── common/          # config por variables de entorno, logging JSON, cliente S3, healthcheck
│   ├── ingestion/       # extractores → bronze (etapa 3)
│   ├── dags/            # DAGs de Airflow (etapa 5)
│   ├── transform/       # proyecto dbt (etapa 4)
│   ├── tests/           # pytest + calidad de datos
│   └── infra/           # Terraform (etapa 7)
└── .github/workflows/   # CI/CD (etapa 8)
```

## Decisiones tomadas

| Decisión | Por qué | Alternativa descartada |
|---|---|---|
| **RustFS** como S3 local | MinIO dejó de publicar imágenes Docker (repo archivado en 2026). RustFS es compatible con S3 y Apache-2.0 | MinIO (sin imágenes mantenidas), LocalStack (más pesado; Glue/Athena son pagos) |
| Sin Kafka/Redpanda (por ahora) | Para ventas simuladas, micro-lotes alcanzan y ahorran RAM y complejidad | Redpanda: queda como extra opcional |
| Config solo por variables de entorno | El mismo código corre en local, Docker y AWS; los secretos no tocan el repo | Valores hardcodeados o un `config.py` con passwords |
| Logging en JSON | Se puede filtrar y contar (CloudWatch Insights, jq) | `print()` o texto libre |
| Versiones de imágenes fijas | El entorno no cambia solo cuando sale una versión nueva | `:latest` |
| Panel con **Streamlit** | Python puro: no hace falta saber HTML/JS | React/Grafana: más potentes, pero hay que aprender otra herramienta |
| Panel alimentado por un **`project.yml`** | Separar datos de presentación: el panel crece editando un YAML, no código | Estados escritos a mano dentro de cada página |
| Puertos en **`127.0.0.1`** | Solo tu PC llega a Postgres, S3 y el panel | `0.0.0.0` (lo que hace Docker por defecto): expuesto a tu red local |

## Qué aprendimos

### Etapa 0 – Preparar la PC
- **Docker** empaqueta cada herramienta con todo lo que necesita en un *contenedor*: funciona igual en cualquier máquina.
- En Windows, Docker corre sobre **WSL2** (un Linux liviano), que necesita la **virtualización** del procesador activada en la BIOS (*SVM Mode* en AMD).

### Etapa 1 – Base del repo y entorno
- **`.env` vs `.env.example`**: el primero tiene tus valores (secretos) y está en `.gitignore`; el segundo es la "plantilla" que sí se sube.
- **docker-compose** define varios servicios que se ven entre sí *por nombre* (`postgres`, `s3`), no por `localhost`. Por eso el servicio `init` pisa `POSTGRES_HOST=postgres`.
- **Volúmenes con nombre**: los datos sobreviven a `docker compose down`; solo `down -v` los borra.
- **Idempotencia**: una operación es idempotente si correrla 1 o 100 veces deja el mismo resultado. `ensure_bucket` primero pregunta si el bucket existe y solo lo crea si falta → se puede reintentar sin miedo. Va a ser clave en la ingesta (no duplicar ventas).
- **Reintentos con espera exponencial** (1s, 2s, 4s…): los servicios recién levantados tardan en responder; reintentar evita que el pipeline se caiga por algo pasajero.
- **Fallar rápido y claro**: si falta una variable, el error dice cuál y qué hacer, en vez de un error críptico 3 pasos después.
- **Códigos de salida**: un script que falla tiene que salir con código ≠ 0 para que Docker, Airflow o CI se enteren.
- **`.gitattributes` con `eol=lf`**: en Windows, los finales de línea CRLF rompen scripts dentro de contenedores Linux.

### Etapa 2 – Panel visual
- **Separar datos de presentación**: el panel lee `project.yml`; para que crezca se edita el YAML, no las páginas.
- **Una fuente de verdad + un test que la valida**: si el YAML "miente" (algo listo que no existe), `pytest` falla.
- **Lógica fuera de la UI**: `panel/` no importa Streamlit (salvo `ui.py`), así se puede testear sin levantar el panel.
- **Caché con vencimiento** (`st.cache_data(ttl=30)`): no se consulta la base en cada clic, pero los datos no quedan viejos.
- **UTC para guardar, hora local para mostrar**: el contenedor vive en UTC; convertimos solo al pintar la pantalla.
- **Mínimo privilegio también en local**: el panel monta el repo en *solo lectura* y los puertos se publican solo en `127.0.0.1`.
- **Inyección SQL**: los nombres de tablas se arman con `sql.Identifier`, nunca con f-strings.
- **Diagramas como código** (Graphviz/DOT): el diagrama de arquitectura se versiona en git como cualquier otro archivo.

## Seguridad y costos

- Nunca hay credenciales reales en el repo: solo `.env.example` con valores de ejemplo.
- Hasta la etapa 7 todo es local y **gratis**. Antes de crear cualquier recurso en AWS se revisa el `terraform plan` y el costo estimado.
- Recordatorio: alerta en **AWS Budgets** y trabajar con un **usuario IAM limitado**, nunca con la cuenta raíz.
