#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Despliegue de Talabartería CMS-CRM a Google Cloud Platform
#
#   Arquitectura:
#     • Cloud Run     → backend (FastAPI) y frontend (Next.js), públicos
#     • Cloud SQL     → PostgreSQL 16 (edición ENTERPRISE, tier db-f1-micro)
#     • Artifact Reg. → imágenes Docker
#     • Cloud Storage → bucket de imágenes de producto, montado en el backend
#
#   Uso:
#     cp gcp.env.example gcp.env   # y completar DB_PASS
#     bash deploy/gcp/deploy.sh
#
#   Es idempotente: los recursos que ya existen se omiten / actualizan.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/gcp.env"
ROOT="$(cd "$HERE/../.." && pwd)"

echo "▶ Proyecto: $PROJECT   Región: $REGION"

# 1) APIs ----------------------------------------------------------------------
echo "▶ Habilitando APIs…"
gcloud services enable run.googleapis.com sqladmin.googleapis.com \
  artifactregistry.googleapis.com cloudbuild.googleapis.com \
  storage.googleapis.com --project "$PROJECT"

# 2) Artifact Registry ---------------------------------------------------------
gcloud artifacts repositories describe "$AR_REPO" --location "$REGION" --project "$PROJECT" >/dev/null 2>&1 \
  || gcloud artifacts repositories create "$AR_REPO" --repository-format=docker \
       --location "$REGION" --project "$PROJECT" --description="Imágenes Talabartería"
gcloud auth configure-docker "$AR_HOST" --quiet

# 3) Bucket de imágenes --------------------------------------------------------
gcloud storage buckets describe "gs://$BUCKET" >/dev/null 2>&1 \
  || gcloud storage buckets create "gs://$BUCKET" --project "$PROJECT" \
       --location "$REGION" --uniform-bucket-level-access

# 4) IAM: la SA de Cloud Run necesita Cloud SQL y el bucket --------------------
gcloud projects add-iam-policy-binding "$PROJECT" \
  --member="serviceAccount:$SA" --role="roles/cloudsql.client" --condition=None >/dev/null
gcloud storage buckets add-iam-policy-binding "gs://$BUCKET" \
  --member="serviceAccount:$SA" --role="roles/storage.objectAdmin" >/dev/null

# 5) Cloud SQL: instancia + base + usuario -------------------------------------
gcloud sql instances describe "$SQL_INSTANCE" --project "$PROJECT" >/dev/null 2>&1 \
  || gcloud sql instances create "$SQL_INSTANCE" --project "$PROJECT" \
       --database-version=POSTGRES_16 --edition=ENTERPRISE --tier=db-f1-micro \
       --region="$REGION" --storage-type=HDD --storage-size=10GB --no-backup \
       --root-password="$DB_PASS"
gcloud sql databases describe "$DB_NAME" --instance "$SQL_INSTANCE" --project "$PROJECT" >/dev/null 2>&1 \
  || gcloud sql databases create "$DB_NAME" --instance "$SQL_INSTANCE" --project "$PROJECT"
gcloud sql users describe "$DB_USER" --instance "$SQL_INSTANCE" --project "$PROJECT" >/dev/null 2>&1 \
  || gcloud sql users create "$DB_USER" --instance "$SQL_INSTANCE" --project "$PROJECT" --password "$DB_PASS"

# 6) Backend: build + push + deploy --------------------------------------------
echo "▶ Backend: build & push…"
docker build --platform linux/amd64 -t "$IMG_BACKEND" "$ROOT/backend"
docker push "$IMG_BACKEND"

# DATABASE_URL via socket Unix de Cloud SQL (sin IP pública).
DB_URL="postgresql+asyncpg://$DB_USER:$DB_PASS@/$DB_NAME?host=/cloudsql/$SQL_CONN"

echo "▶ Backend: deploy a Cloud Run…"
gcloud run deploy "$BACKEND_SVC" --project "$PROJECT" --region "$REGION" \
  --image "$IMG_BACKEND" --allow-unauthenticated \
  --execution-environment gen2 \
  --port 8000 \
  --add-cloudsql-instances "$SQL_CONN" \
  --add-volume "name=media,type=cloud-storage,bucket=$BUCKET" \
  --add-volume-mount "volume=media,mount-path=/app/media" \
  --set-env-vars "ENVIRONMENT=production,DATABASE_URL=$DB_URL,MEDIA_LOCAL_PATH=/app/media,CATALOG_SHOW_PRICES=$CATALOG_SHOW_PRICES,CATALOG_CURRENCY_SYMBOL=$CATALOG_CURRENCY_SYMBOL,WHATSAPP_CATALOG_PHONE=$WHATSAPP_CATALOG_PHONE" \
  --memory 512Mi --cpu 1 --min-instances 0 --max-instances 2

BACKEND_URL="$(gcloud run services describe "$BACKEND_SVC" --project "$PROJECT" --region "$REGION" --format='value(status.url)')"
echo "   Backend: $BACKEND_URL"

# 7) Frontend: build (con NEXT_PUBLIC_API_URL) + push + deploy -----------------
echo "▶ Frontend: build & push…"
docker build --platform linux/amd64 -t "$IMG_FRONTEND" \
  --build-arg "NEXT_PUBLIC_API_URL=$BACKEND_URL" \
  --build-arg "NEXT_PUBLIC_WHATSAPP_PHONE=$WHATSAPP_CATALOG_PHONE" \
  --build-arg "CATALOG_SHOW_PRICES=$CATALOG_SHOW_PRICES" \
  --build-arg "CATALOG_CURRENCY_SYMBOL=$CATALOG_CURRENCY_SYMBOL" \
  "$ROOT/frontend"
docker push "$IMG_FRONTEND"

echo "▶ Frontend: deploy a Cloud Run…"
gcloud run deploy "$FRONTEND_SVC" --project "$PROJECT" --region "$REGION" \
  --image "$IMG_FRONTEND" --allow-unauthenticated \
  --set-env-vars "NEXT_PUBLIC_API_URL=$BACKEND_URL,INTERNAL_API_URL=$BACKEND_URL" \
  --memory 512Mi --cpu 1 --min-instances 0 --max-instances 2

FRONTEND_URL="$(gcloud run services describe "$FRONTEND_SVC" --project "$PROJECT" --region "$REGION" --format='value(status.url)')"
echo "   Frontend: $FRONTEND_URL"

# 8) Cerrar el círculo: backend conoce el origen del frontend (CORS, QR) -------
echo "▶ Actualizando backend con URLs definitivas…"
gcloud run services update "$BACKEND_SVC" --project "$PROJECT" --region "$REGION" \
  --update-env-vars "CORS_ORIGINS=$FRONTEND_URL,CATALOG_PUBLIC_BASE_URL=$FRONTEND_URL,MEDIA_BASE_URL=$BACKEND_URL"

echo ""
echo "✅ Listo"
echo "   Catálogo : $FRONTEND_URL/catalogo"
echo "   Revista  : $FRONTEND_URL/revista"
echo "   Dashboard: $FRONTEND_URL/dashboard"
echo "   API docs : $BACKEND_URL/docs"
