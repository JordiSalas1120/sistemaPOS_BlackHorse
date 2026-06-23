from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuditMiddleware)

# ── Routers ───────────────────────────────────────────────────────────────────
from src.infrastructure.api.v1.router import api_router

app.include_router(api_router, prefix="/api/v1")


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
