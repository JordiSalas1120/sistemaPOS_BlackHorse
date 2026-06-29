# Estado del Proyecto — Talabartería CMS-CRM

> Documento de continuidad: **dónde nos quedamos** y cómo retomar.
> Última actualización: **2026-06-29**

---

## 1. Resumen

CMS y CRM para una talabartería (artículos de cuero). Backend FastAPI + Next.js + PostgreSQL, arquitectura hexagonal. Desarrollo local con Docker Compose; **desplegado en GCP** para pruebas en línea.

## 2. Qué está hecho (sprints)

| Sprint | Estado | Spec |
|--------|--------|------|
| Base CMS/CRM (productos, clientes, inventario, ventas/POS, precios, auditoría) | ✅ | — |
| Sprint 1 — Taller / BOM (recetas) | ✅ | `docs/specs/sprint-1-taller-bom.md` |
| Sprint 2 — Producción (órdenes) | ✅ | `docs/specs/sprint-2-produccion.md` |
| Sprint 3 — Vitrina pública de catálogo + imágenes + WhatsApp | ✅ | `docs/specs/sprint-3-catalogo.md` |
| Sprint 4 — Catálogo Revista (PDF editorial, QR, marca de agua, ficha técnica) | ✅ | `docs/specs/sprint-4-catalogo-revista.md` |

**Último trabajo funcional**: ficha técnica tipo "specs de celular/computadora" en el PDF del catálogo (`/revista`), a partir de los atributos JSONB del producto. Helper compartido en `frontend/src/lib/catalog-attributes.ts` (`getSpecs`, `labelFor`).

## 3. Despliegue en GCP (en línea)

- **Proyecto**: `n8n-conexion-474818` · **Región**: `southamerica-east1` (São Paulo)
- **Frontend**: https://talabarteria-frontend-640221760605.southamerica-east1.run.app
- **Backend / API docs**: https://talabarteria-backend-640221760605.southamerica-east1.run.app/docs

Rutas de prueba:
- Catálogo: `…frontend…/catalogo`
- Revista (PDF): `…frontend…/revista`
- Dashboard: `…frontend…/dashboard`

Arquitectura: Cloud Run (backend + frontend) · Cloud SQL PostgreSQL 16 (`talabarteria-db`, db-f1-micro) · Cloud Storage (bucket de imágenes montado en el backend) · Artifact Registry. El esquema de BD se autocrea al arrancar el backend (no usa Alembic en la nube).

**Infra versionada**: `deploy/gcp/` (`deploy.sh` idempotente + `README.md`). El secreto (`gcp.env`) está gitignored.
Redeploy tras cambios: `bash deploy/gcp/deploy.sh`.

Detalle completo: ver `deploy/gcp/README.md`.

## 4. Pendientes / próximos pasos

- [ ] **Cargar datos de prueba** en la nube (productos con atributos + imágenes) para validar la ficha técnica del PDF.
- [ ] Configurar el **número de WhatsApp real** (hoy `591XXXXXXXXX` placeholder) → env `NEXT_PUBLIC_WHATSAPP_PHONE` (frontend) y `WHATSAPP_CATALOG_PHONE` (backend).
- [ ] **Autenticación del dashboard** (hoy `/dashboard` es público — no compartir la URL).
- [ ] Documentar/automatizar pipeline (GitHub Actions) — aún se despliega manual con `deploy.sh`.
- [ ] (Opcional) Ajustes de diseño del PDF según cómo se vea con datos reales.

## 5. Cómo retomar

**Local** (desarrollo):
```bash
cp .env.example .env   # si no existe
docker-compose up
# Frontend http://localhost:3000 · API http://localhost:8000/docs
```

**Nube** (redeploy tras cambios):
```bash
cd deploy/gcp && bash deploy.sh        # requiere gcp.env con DB_PASS
```

**Controlar costo de la BD en la nube** (lo único que factura inactivo, ~8 USD/mes):
```bash
gcloud sql instances patch talabarteria-db --activation-policy NEVER   # detener
gcloud sql instances patch talabarteria-db --activation-policy ALWAYS  # reanudar
```

## 6. Cambios recientes no relacionados a una feature

- `backend/src/config.py` + `main.py`: **CORS configurable** vía env `CORS_ORIGINS` (antes fijo a localhost), necesario para la nube.
- `frontend/Dockerfile`: acepta `NEXT_PUBLIC_*` como **build-args** (Next.js los hornea en build).
