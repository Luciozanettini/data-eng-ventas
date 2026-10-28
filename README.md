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
| 2 | Panel visual (Streamlit) | ⏳ pendiente |
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
| Consola de RustFS (S3 local) | http://localhost:9001 | Ver buckets y archivos (usuario/clave: `S3_ACCESS_KEY` / `S3_SECRET_KEY` de tu `.env`) |
| API S3 local | http://localhost:9000 | La usa boto3 |
| Postgres | `localhost:5432` | Warehouse local |

Apagar: `docker compose down` (conserva datos) · Borrar todo: `docker compose down -v`.

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
├── dashboard/           # panel Streamlit (etapa 2)
├── src/
│   ├── common/          # config por variables de entorno, logging JSON, healthcheck
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

## Seguridad y costos

- Nunca hay credenciales reales en el repo: solo `.env.example` con valores de ejemplo.
- Hasta la etapa 7 todo es local y **gratis**. Antes de crear cualquier recurso en AWS se revisa el `terraform plan` y el costo estimado.
- Recordatorio: alerta en **AWS Budgets** y trabajar con un **usuario IAM limitado**, nunca con la cuenta raíz.
