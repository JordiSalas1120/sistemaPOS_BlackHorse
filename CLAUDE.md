# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CMS y CRM para una tienda de talabartería (artículos de cuero). Gestiona productos, inventario, clientes y ventas con precios diferenciados retail/mayorista, automatización CRM y auditoría/exportación completa.

**Despliegue**: Local con Docker Compose. Un solo comando levanta todo.

## Stack

| Capa | Tecnología |
|------|-----------|
| Backend | FastAPI 0.115 (Python 3.12) |
| Frontend | Next.js 14 (TypeScript, App Router) |
| Base de datos | PostgreSQL 16 |
| ORM + Migraciones | SQLAlchemy 2.0 async + Alembic |
| Exportación | pandas / openpyxl + TXT tickets |
| Estado frontend | Zustand |
| Validación frontend | Zod + react-hook-form |

## Comandos de desarrollo

### Docker (recomendado)
```bash
# Copiar variables de entorno (una sola vez)
cp .env.example .env

# Levantar todo (backend + frontend + postgres) con hot-reload
docker-compose up

# Primera vez o tras cambiar dependencias
docker-compose up --build

# Aplicar migraciones (primera vez que se levanta la BD)
docker exec talabarteria_backend alembic upgrade head

# Solo la base de datos
docker-compose up postgres
```

### Backend (sin Docker)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

uvicorn src.main:app --reload        # http://localhost:8000

# Migraciones
alembic upgrade head
alembic revision --autogenerate -m "descripcion"
alembic downgrade -1

# Tests
pytest
pytest tests/unit/domain/test_pricing_service.py   # test individual
pytest --cov=src --cov-report=term-missing

# Linting
ruff check src/
ruff format src/
```

### Frontend (sin Docker)
```bash
cd frontend
npm install
npm run dev      # http://localhost:3000
npm run build
npm run lint
```

### URLs
- Frontend: http://localhost:3000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Arquitectura Hexagonal — Reglas

```
domain/         ──→ NO importa nada externo (ni SQLAlchemy, ni FastAPI, ni pydantic)
application/    ──→ importa domain/ y ports/. NUNCA importa infrastructure/
infrastructure/ ──→ implementa los puertos. Importa todo lo necesario
main.py         ──→ único lugar donde se instancian adaptadores y se inyectan dependencias
```

**Estructura backend** (`backend/src/`):
```
src/
├── config.py              # Pydantic Settings — DATABASE_URL, DEBUG, etc.
├── dependencies.py        # Factories para repos y services vía FastAPI Depends
├── domain/
│   ├── models/            # Dataclasses puros: Client, Product, Sale, Inventory, PriceRule, AuditLog + enums (StrEnum)
│   └── services/          # pricing_service, inventory_service, crm_tagging_service
├── application/
│   ├── ports/             # Interfaces abstractas: RepositoryPort × 7, ExporterPort, MessengerPort
│   ├── use_cases/         # products/, inventory/, clients/, sales/, price_rules/ — un archivo por caso de uso
│   ├── dtos/              # Input/output DTOs por módulo
│   └── exceptions.py      # NotFoundError, InsufficientStockError, etc.
└── infrastructure/
    ├── database/
    │   ├── connection.py  # Engine async + sessionmaker
    │   ├── base.py        # DeclarativeBase
    │   └── orm_models/    # Modelos SQLAlchemy (separados de entidades de dominio)
    ├── adapters/
    │   ├── postgres_repo/ # products, inventory, categories, audit_log, clients, sales, price_rules
    │   ├── excel_exporter/ # ExcelExporter con pandas/openpyxl + auto-ancho de columnas
    │   └── txt_exporter/  # TxtTicketExporter — ticket POS de 40 chars
    └── api/v1/
        ├── endpoints/     # products, inventory, clients, sales, price_rules, exports
        ├── schemas/       # Pydantic request/response por módulo
        ├── middleware/    # audit_middleware.py — loguea todas las mutaciones HTTP
        └── router.py      # Agrega todos los routers bajo /api/v1
```

## Base de Datos — Tablas

| Tabla | Propósito |
|-------|-----------|
| `categories` | Catálogo: Equino, Bovino, Accesorios, Herrería (seed en migración) |
| `clients` | Clientes con tags `TEXT[]` (GIN index), tipo retail/wholesale |
| `products` | SKU único, precios retail/wholesale, atributos `JSONB` (GIN index) |
| `inventory` | 1 fila por producto, `NUMERIC(12,3)` para metros/unidades |
| `inventory_movements` | Trazabilidad: purchase, sale, adjustment, return, loss |
| `price_rules` | Descuentos por volumen, tipo de cliente o categoría |
| `sales` | Numeración `VTA-YYYY-NNNNN`, snapshot de precios al momento de venta |
| `sale_items` | Detalle con precio y descuento congelados |
| `audit_logs` | Payload JSONB before/after para toda mutación |

**Migración única**: `backend/alembic/versions/001_initial_schema.py` — crea las 9 tablas y hace seed de las 4 categorías.

## Lógica de Negocio Clave

**Precios** (`domain/services/pricing_service.py`): `calculate_unit_price()` selecciona la `PriceRule` activa de mayor prioridad que coincida con `client_type`, `min_quantity`, `product_id`/`category_id` y vigencia. Retorna `(unit_price, discount_per_unit)`.

**Etiquetado CRM** (`domain/services/crm_tagging_service.py`): `apply_post_sale_tags()` agrega `mayorista` para ventas wholesale y `recordatorio_mantenimiento` para ventas de categorías equino/bovino. No duplica tags.

**Auditoría** (`infrastructure/api/v1/middleware/audit_middleware.py`): Middleware que loguea toda mutación HTTP (POST/PUT/PATCH/DELETE con 2xx) en `audit_logs`. Abre su propia sesión de BD; los errores de log son silenciosos para no romper el flujo.

**Numeración de ventas**: `SaleRepository.next_sale_number(year)` hace `COUNT(*)` por año — formato `VTA-2026-00001`.

**Consistencia transaccional**: Todos los repos en un request comparten la misma `AsyncSession` gracias al caching de `Depends`. El stock se descuenta y la venta se crea en la misma transacción.

## Frontend

- `src/lib/api.ts` — cliente axios apuntando a `NEXT_PUBLIC_API_URL/api/v1`
- `src/store/cart.store.ts` — Zustand: carrito POS con totales, descuentos y limpieza post-venta
- `src/lib/formatters.ts` — `formatCurrency()` (ARS, 2 decimales) y `formatDate()` (es-AR)
- `src/types/index.ts` — interfaces TypeScript que mapean 1:1 las respuestas del backend
- `src/services/` — `products`, `clients`, `inventory`, `sales`, `price-rules`
- `src/schemas/` — Zod: `product.schema`, `client.schema`, `sale.schema` (incluye `adjustStockSchema`)
- `src/components/ui/` — `Button`, `Modal`, `FormField`/`SelectField`/`TextAreaField`
- Paleta `brand-*` en `tailwind.config.ts` — tonos cuero/marrón

**Reglas de frontend:**
- Nunca llamar la API directamente desde componentes — usar `src/services/`
- Validar con Zod en `src/schemas/` antes de enviar al backend

**Páginas implementadas** (todas bajo `src/app/dashboard/`):
| Ruta | Componente principal | Descripción |
|------|----------------------|-------------|
| `/dashboard` | `page.tsx` | Cards de navegación |
| `/dashboard/productos` | `ProductForm` | CRUD + toggle activo + export Excel |
| `/dashboard/clientes` | `ClientForm` | CRUD + gestión de tags CRM |
| `/dashboard/inventario` | `AdjustStockForm` | Snapshot + alertas stock bajo + ajustes |
| `/dashboard/ventas` | `POSForm` | POS completo + detalle + ticket + export Excel |
| `/dashboard/precios` | inline | CRUD reglas de precio + toggle activo |
