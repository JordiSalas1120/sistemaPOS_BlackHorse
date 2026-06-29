import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select

from src.config import settings
from src.infrastructure.database.connection import async_session_factory, engine
from src.infrastructure.database.base import Base
from src.infrastructure.database.orm_models.category_orm import CategoryORM
from src.infrastructure.api.v1.middleware.audit_middleware import AuditMiddleware

_SEED_CATEGORIES = [
    {"name": "Equino",     "slug": "equino",     "description": "Artículos para caballos: monturas, riendas, albardas"},
    {"name": "Bovino",     "slug": "bovino",     "description": "Artículos para ganadería: sogas, bozales, yugos"},
    {"name": "Accesorios", "slug": "accesorios", "description": "Cinturones, billeteras, carteras y marroquinería"},
    {"name": "Herrería",   "slug": "herreria",   "description": "Hebillas, argollas, herramientas y ferretería"},
    # Categorías del taller (equivalen al seed de la migración 002 — necesarias
    # cuando la BD se inicializa vía create_all en desarrollo, sin Alembic).
    {"name": "Cueros y Pieles",        "slug": "cueros-pieles",        "description": "Materias primas: cueros y pieles"},
    {"name": "Hebillería y Herrajes",  "slug": "hebilleria-herrajes",  "description": "Hebillas, herrajes y metales"},
    {"name": "Coronas y Adornos",      "slug": "coronas-adornos",      "description": "Adornos y apliques decorativos"},
    {"name": "Hilos y Telas",          "slug": "hilos-telas",          "description": "Hilos, telas y textiles"},
    {"name": "Insumos de Taller",      "slug": "insumos-taller",       "description": "Insumos consumibles del taller"},
    {"name": "Monturas",               "slug": "monturas",             "description": "Productos terminados: monturas"},
    {"name": "Hakimas y Jaquimas",     "slug": "hakimas-jaquimas",     "description": "Hakimas y jaquimas"},
    {"name": "Mantas y Sudaderos",     "slug": "mantas-sudaderos",     "description": "Mantas y sudaderos"},
    {"name": "Riendas y Bridas",       "slug": "riendas-bridas",       "description": "Riendas y bridas"},
    {"name": "Cinchería",              "slug": "cincheria",            "description": "Cinchas y cinchería"},
    {"name": "Ganadería",              "slug": "ganaderia",            "description": "Artículos de ganadería"},
    {"name": "Pet Shop",               "slug": "pet-shop",             "description": "Artículos para mascotas"},
    {"name": "Herramientas de Taller", "slug": "herramientas-taller",  "description": "Herramientas del taller"},
]


async def _seed_categories() -> None:
    async with async_session_factory() as session:
        count = (await session.execute(select(func.count()).select_from(CategoryORM))).scalar()
        if count == 0:
            session.add_all([CategoryORM(**cat) for cat in _SEED_CATEGORIES])
            await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: crear tablas si no existen, luego sembrar categorías base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _seed_categories()
    yield
    # Shutdown
    await engine.dispose()


_TAGS_METADATA = [
    {
        "name": "Productos",
        "description": "CRUD de productos del catálogo. Incluye categoría, precios retail/mayorista, unidad de medida y atributos dinámicos en JSONB.",
    },
    {
        "name": "Categorías",
        "description": "Categorías base del catálogo: **Equino**, **Bovino**, **Accesorios** y **Herrería**. Solo lectura — se configuran en la migración inicial.",
    },
    {
        "name": "Inventario",
        "description": "Control de stock en tiempo real. Cada movimiento (compra, venta, ajuste, devolución, merma) queda trazado con cantidad antes/después.",
    },
    {
        "name": "Clientes",
        "description": "Ficha de cliente con segmentación retail/mayorista, tags CRM y historial de compras. Los tags se gestionan individualmente para facilitar la automatización.",
    },
    {
        "name": "Ventas",
        "description": "Punto de venta (POS). Al crear una venta se aplican automáticamente las reglas de precio activas, se descuenta el stock y se etiquetan los clientes según el CRM.",
    },
    {
        "name": "Reglas de precios",
        "description": "Motor de descuentos configurable. Soporta descuentos por porcentaje o monto fijo, con filtros por tipo de cliente, cantidad mínima, categoría o producto. Se aplica la regla de mayor prioridad.",
    },
    {
        "name": "Exportaciones",
        "description": "Descargas en formato Excel (pandas/openpyxl) para productos, inventario y ventas. Ticket de venta en formato TXT de 40 caracteres compatible con impresoras POS.",
    },
    {
        "name": "Catálogo Público",
        "description": "Endpoints públicos de la vitrina. Sin autenticación. Solo lectura. "
                       "Expone únicamente productos con `show_in_catalog=True` e `is_active=True`.",
    },
    {
        "name": "Imágenes de Producto",
        "description": "Gestión admin de imágenes de producto (subida, orden, principal, borrado).",
    },
    {
        "name": "Health",
        "description": "Endpoints de diagnóstico para monitoreo del servicio.",
    },
]

app = FastAPI(
    title="Talabartería CMS-CRM",
    version=settings.app_version,
    description="""
## Sistema de Gestión para Talabartería

API REST para el CMS y CRM de una tienda de artículos de cuero (Bolivia).
Construida con arquitectura hexagonal: **domain → application → infrastructure**.

---

### Flujo principal

1. **Crear productos** con SKU automático (ej: `EQU-00001`) y precios retail/mayorista
2. **Configurar reglas de precio** por volumen, tipo de cliente o categoría
3. **Registrar clientes** con segmentación retail/mayorista y tags CRM
4. **Registrar ventas** desde el POS — el motor aplica descuentos, descuenta stock y etiqueta clientes
5. **Monitorear inventario** con alertas de stock bajo y historial de movimientos
6. **Exportar datos** a Excel o imprimir tickets TXT

---

### Autenticación

Actualmente sin autenticación. El campo `X-Actor` en los headers identifica al operador
para el registro de auditoría. En producción se integrará JWT.

---

### Convenciones

- Todos los precios en **bolivianos (BOB)**
- Fechas en **ISO 8601 UTC**
- IDs en **UUID v4**
- Paginación: `skip` + `limit` (máx. 200)
""",
    openapi_tags=_TAGS_METADATA,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuditMiddleware)

# ── Archivos estáticos: imágenes subidas ───────────────────────────────────────
# En producción nginx sirve /media/ directamente; en desarrollo lo sirve FastAPI.
os.makedirs(settings.media_local_path, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.media_local_path), name="media")

# ── Routers ───────────────────────────────────────────────────────────────────
from src.infrastructure.api.v1.router import api_router
from src.infrastructure.api.v1.endpoints.catalog import router as catalog_router

app.include_router(api_router, prefix="/api/v1")

# El router de catálogo es público (solo-lectura GET): se registra aparte para
# no pasar por AuditMiddleware ni la futura autenticación del dashboard.
app.include_router(catalog_router, prefix="/api/v1/catalog")


@app.get("/", tags=["Health"], summary="Health check")
async def root():
    """Verifica que el servicio esté en línea."""
    return {"status": "ok", "service": settings.app_name, "version": settings.app_version}


@app.get("/health", tags=["Health"], summary="Estado detallado del servicio")
async def health():
    """Retorna el estado del servicio y el entorno actual."""
    return {
        "status": "healthy",
        "environment": settings.environment,
        "version": settings.app_version,
    }
