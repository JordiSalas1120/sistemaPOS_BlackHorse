# Despliegue en Google Cloud Platform

Despliegue del CMS-CRM de Talabartería en GCP para pruebas en línea.
Proyecto: **`n8n-conexion-474818`** · Región: **`southamerica-east1`** (São Paulo).

## Arquitectura

```
                 Internet
                    │
        ┌───────────┴────────────┐
        ▼                        ▼
  Cloud Run                 Cloud Run
  frontend (Next.js)        backend (FastAPI)
        │                    │      │
        │ NEXT_PUBLIC_API_URL│      │ socket /cloudsql
        └────────────────────┘      ├──────────► Cloud SQL (PostgreSQL 16)
                                     │
                                     └── volumen montado /app/media ──► Cloud Storage (bucket)
```

| Componente | Servicio GCP | Notas |
|-----------|--------------|-------|
| Backend FastAPI | Cloud Run (`talabarteria-backend`) | Público. Conecta a Cloud SQL por socket Unix. Sirve `/media` desde el bucket. |
| Frontend Next.js | Cloud Run (`talabarteria-frontend`) | Público. `NEXT_PUBLIC_API_URL` apunta al backend. |
| Base de datos | Cloud SQL `talabarteria-db` | PostgreSQL 16, edición ENTERPRISE, tier `db-f1-micro`, HDD 10 GB, sin backups. |
| Imágenes de producto | Cloud Storage `…-talabarteria-media` | Montado como volumen en el backend (gcsfuse, gen2). Persisten entre reinicios. |
| Imágenes Docker | Artifact Registry `talabarteria` | |

El esquema de BD se crea solo al arrancar el backend (`Base.metadata.create_all` en `main.py`) y siembra las categorías base. **No** se ejecuta Alembic en este despliegue.

## Requisitos

- `gcloud` autenticado con permisos de Owner/Editor en el proyecto.
- Docker en ejecución local (las imágenes se construyen y pushean desde la máquina).
- Billing habilitado en el proyecto.

## Cómo desplegar

```bash
cd deploy/gcp
cp gcp.env.example gcp.env     # completar DB_PASS con un password seguro
bash deploy.sh
```

El script es **idempotente**: omite recursos ya creados y actualiza los servicios de Cloud Run en cada corrida. Para redeployar tras cambios de código basta volver a correr `bash deploy.sh`.

## Variables de entorno (Cloud Run)

**Backend** (`--set-env-vars`):
- `ENVIRONMENT=production`
- `DATABASE_URL=postgresql+asyncpg://USER:PASS@/DB?host=/cloudsql/CONN` (socket, sin IP pública)
- `MEDIA_LOCAL_PATH=/app/media` · `MEDIA_BASE_URL=<url backend>`
- `CORS_ORIGINS=<url frontend>` · `CATALOG_PUBLIC_BASE_URL=<url frontend>`
- `CATALOG_SHOW_PRICES`, `CATALOG_CURRENCY_SYMBOL`, `WHATSAPP_CATALOG_PHONE`

**Frontend** (build-args + env):
- `NEXT_PUBLIC_API_URL=<url backend>` (se "hornea" en build; también como env runtime para SSR)
- `INTERNAL_API_URL=<url backend>` (fetch server-side del catálogo)

## Controlar costos

El gasto fijo es **Cloud SQL** (~8 USD/mes) aunque no se use. Para pausarlo entre pruebas:

```bash
gcloud sql instances patch talabarteria-db --activation-policy NEVER   # detener
gcloud sql instances patch talabarteria-db --activation-policy ALWAYS  # reanudar
```

Cloud Run escala a cero (no cobra inactivo). El bucket cobra solo por almacenamiento (centavos).

## Limpieza total

```bash
gcloud run services delete talabarteria-backend talabarteria-frontend --region southamerica-east1
gcloud sql instances delete talabarteria-db
gcloud storage rm -r gs://n8n-conexion-474818-talabarteria-media
gcloud artifacts repositories delete talabarteria --location southamerica-east1
```

## Notas de seguridad

- El **dashboard** (`/dashboard`) aún **no tiene autenticación**. Mientras siga así, no compartir esa URL públicamente — cualquiera podría gestionar productos. El catálogo (`/catalogo`, `/revista`) sí es público a propósito.
- El password de la BD vive en `gcp.env` (gitignored) y en las env-vars del servicio. Para producción real, migrar a Secret Manager.
