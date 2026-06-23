# Sprint 3 — Vitrina Pública de Catálogo

> **Estado**: Especificación lista para implementar
> **Fecha**: 2026-06-22
> **Prerrequisito**: Sprint 2 completado (`product_type`, `show_in_catalog`, tablas `bom`, `bom_items`, `production_orders`, `production_order_items` presentes)

---

## 1. Objetivo y Alcance

### Objetivo

Implementar una vitrina pública navegable por URL sin autenticación que el negocio comparte por WhatsApp. El cliente puede ver fotos, características y atributos de cada producto, y con un solo toque inicia una conversación de WhatsApp con el negocio.

### Alcance del Sprint 3

**Incluido:**
- Migración 004: tabla `product_images` con soporte multi-imagen por producto
- Modelos de dominio: `ProductImage`, `CatalogProduct`, `CatalogCategory`
- Variables de entorno nuevas en `config.py` para catálogo y WhatsApp
- Puerto `CatalogRepositoryPort` (solo lectura pública)
- Puerto `ProductImageRepositoryPort` (gestión admin de imágenes)
- Endpoint de subida de imágenes: `POST /api/v1/products/{id}/images` y endpoints de gestión (PUT primary, PUT reorder, DELETE)
- Router público `/api/v1/catalog` sin middleware de auditoría ni auth
- Frontend: rutas `src/app/catalogo/` completamente fuera de `/dashboard/`
- Componentes: `CatalogLayout`, `ProductCard`, `ImageGallery`, `WhatsAppButton`, `CategoryFilter`
- SEO con Next.js 14 metadata API (Open Graph para preview en WhatsApp)
- Admin: toggle "Mostrar en catálogo" y galería de imágenes en `ProductForm.tsx`
- Services TypeScript: `catalog.service.ts`, `product-images.service.ts`
- Docker Compose: volumen compartido `/media/` entre backend y nginx

**Excluido (Sprint 4+):**
- Carrito de compra público
- Pago en línea
- Stock visible en catálogo público
- Integración con S3 (documentada como alternativa, no implementada)
- Internacionalización (i18n)
- Búsqueda con Elasticsearch

---

## 2. Decisiones de Arquitectura

### 2.1 Por qué `/api/v1/catalog/*` separado del dashboard

Los endpoints del dashboard (`/api/v1/products`, `/api/v1/clients`, etc.) pasan por `AuditMiddleware`, que loguea toda mutación en `audit_logs`. Los endpoints públicos del catálogo son solo lectura (`GET`) y nunca deben generar registros de auditoría — un bot de Google que indexe el catálogo no debe llenar la tabla `audit_logs`.

Además, en el futuro se añadirá autenticación (JWT) al dashboard. Tener un prefijo separado permite aplicar el middleware de autenticación al router del dashboard mediante `dependencies=[Depends(require_auth)]` en `include_router()` sin afectar el catálogo público.

```python
# main.py — separación clara de routers
app.include_router(api_router, prefix="/api/v1")           # dashboard — con AuditMiddleware
app.include_router(catalog_router, prefix="/api/v1/catalog")  # público — sin auth, sin audit
```

### 2.2 Por qué tabla `product_images` en lugar de JSONB array

Tres razones concretas:

1. **Normalización y consultas**: Con JSONB no se puede hacer `ORDER BY sort_order` ni `WHERE is_primary = true` eficientemente. Con tabla relacional se obtiene un índice B-tree en `(product_id, sort_order)`.

2. **Integridad referencial**: La FK `product_images.product_id → products.id ON DELETE CASCADE` garantiza que al eliminar un producto se eliminan todas sus imágenes. Con JSONB esto requiere lógica adicional en la aplicación.

3. **Tamaño de fila**: PostgreSQL tiene un límite práctico de ~8KB por fila TOAST-inlineada. Un array JSONB con 10 URLs de 500 chars + alt_text ya supera ese umbral. Con tabla separada, la fila de `products` permanece pequeña y la query de catálogo puede hacer JOIN solo cuando necesita imágenes.

La columna `image_url` en `products` se mantiene para compatibilidad con los sprints 1 y 2. Se usa como fallback si `product_images` está vacío.

### 2.3 Estrategia de imágenes: URL, no binario

El backend guarda la imagen en disco (`/media/{product_id}/{filename}`) y persiste la URL pública en la base de datos. El binario nunca entra a PostgreSQL. Esto permite:

- Migrar a S3 sin cambiar el esquema de BD — solo cambia el valor de `MEDIA_BASE_URL`
- Servir imágenes directamente desde nginx con `alias /media/` sin pasar por FastAPI
- Invalidar caché de CDN por URL sin tocar la BD

El campo `url` en `product_images` almacena la URL completa (`http://dominio.com/media/uuid/foto.webp`), no el path relativo. El backend construye la URL al momento de guardar usando `MEDIA_BASE_URL`.

### 2.4 Por qué Next.js 14 metadata API y no react-helmet

Next.js 14 App Router renderiza `generateMetadata()` en el servidor antes de enviar HTML. WhatsApp y otros scrapers de Open Graph leen el HTML del primer response — sin JavaScript. `react-helmet` requiere que el JS se ejecute en el cliente, lo que hace que los bots vean `<meta>` vacíos.

Con `generateMetadata()` en Server Components, el `<og:image>` con la foto del producto aparece en el HTML inicial, permitiendo el preview de thumbnail cuando alguien comparte el link en WhatsApp.

### 2.5 Rutas públicas fuera de `/dashboard/`

`src/app/dashboard/layout.tsx` incluye el `Sidebar` y requiere (en el futuro) autenticación. Las rutas de catálogo viven en `src/app/catalogo/` con su propio `layout.tsx` — un header público con logo y datos de contacto, sin sidebar ni verificación de sesión. Next.js App Router aplica el layout más cercano en el árbol de directorios, por lo que no hay riesgo de que el `DashboardLayout` envuelva páginas del catálogo.

---

## 3. Migración 004 — SQL Completo

Archivo: `backend/alembic/versions/004_product_images.py`

```python
"""product_images table

Revision ID: 004
Revises: 003
Create Date: 2026-06-22
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── product_images ────────────────────────────────────────────────────────
    op.create_table(
        "product_images",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("alt_text", sa.String(200), nullable=True),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_primary", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Índice para listar imágenes de un producto en orden
    op.create_index(
        "ix_product_images_product_id_sort",
        "product_images",
        ["product_id", "sort_order"],
    )

    # Índice parcial: garantiza unicidad de is_primary=true por producto
    # Solo existe un registro con is_primary=true por product_id
    op.execute(
        """
        CREATE UNIQUE INDEX uq_product_images_primary
        ON product_images (product_id)
        WHERE is_primary = true
        """
    )

    # Agregar show_in_catalog a products si no existe (Sprint 1 pudo haberla agregado)
    # Se usa IF NOT EXISTS para idempotencia
    op.execute(
        """
        ALTER TABLE products
        ADD COLUMN IF NOT EXISTS show_in_catalog BOOLEAN NOT NULL DEFAULT false
        """
    )
    op.create_index(
        "ix_products_show_in_catalog",
        "products",
        ["show_in_catalog"],
        postgresql_where=sa.text("show_in_catalog = true"),
    )


def downgrade() -> None:
    op.drop_index("ix_products_show_in_catalog", table_name="products")
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS show_in_catalog")
    op.drop_index("uq_product_images_primary", table_name="product_images")
    op.drop_index("ix_product_images_product_id_sort", table_name="product_images")
    op.drop_table("product_images")
```

**Nota sobre `is_primary`**: El índice parcial único (`WHERE is_primary = true`) es la restricción de base de datos. Al marcar una imagen como primary en la aplicación, primero se hace `UPDATE product_images SET is_primary = false WHERE product_id = $1` y luego `UPDATE product_images SET is_primary = true WHERE id = $2`. Ambas operaciones van en la misma transacción para evitar violar el índice.

---

## 4. Modelos de Dominio

Archivo: `backend/src/domain/models/catalog.py`

```python
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass
class ProductImage:
    """Imagen de un producto. El binario vive en /media/, aquí solo la URL."""
    id: UUID
    product_id: UUID
    url: str                          # URL completa: http://host/media/{product_id}/foto.webp
    sort_order: int
    is_primary: bool
    created_at: datetime
    alt_text: str | None = None


@dataclass
class CatalogProduct:
    """
    Proyección pública de un producto para el catálogo.

    Campos deliberadamente AUSENTES (no exponer al público):
    - wholesale_price  → precio mayorista interno
    - cost_price       → costo de producción/compra
    - low_stock_threshold → dato operativo interno
    - quantity_on_hand → nivel de stock
    - sold_by / created_by → datos operativos
    """
    id: UUID
    sku: str
    name: str
    description: str | None
    category_id: UUID
    category_name: str
    category_slug: str
    unit: str                         # ProductUnit.value
    attributes: dict                  # JSONB: {"leather_type": "vaqueta", ...}
    images: list[ProductImage]
    is_active: bool
    show_in_catalog: bool
    base_price: Decimal | None = None  # None si CATALOG_SHOW_PRICES=False


@dataclass
class CatalogCategory:
    """Categoría con conteo de productos visibles en catálogo."""
    id: UUID
    name: str
    slug: str
    description: str | None
    product_count: int                 # productos activos con show_in_catalog=true
```

**Regla de dominio**: `CatalogProduct` no importa ni hereda de `Product`. Es una proyección independiente que garantiza en tiempo de compilación que los campos privados no se "filtren" por accidente en un futuro refactor.

---

## 5. Configuración — Variables de Entorno

Archivo: `backend/src/config.py` (sección a agregar)

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Aplicación
    app_name: str = "Talabartería CMS-CRM"
    app_version: str = "0.1.0"
    environment: str = "development"

    # Base de datos
    database_url: str

    # Seguridad
    secret_key: str = "changeme"

    # WhatsApp Business API (existente — Sprint 1/2)
    whatsapp_api_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_verify_token: str = ""

    # ── NUEVO Sprint 3 ────────────────────────────────────────────────────────

    # Número del negocio para el botón "Consultar por WhatsApp" del catálogo.
    # Formato internacional sin +: "591XXXXXXXXX" (Bolivia) o "54911XXXXXXXX" (Argentina).
    whatsapp_catalog_phone: str = "591XXXXXXXXX"

    # Template del mensaje pre-llenado. Soporta {product_name} y {sku}.
    whatsapp_message_template: str = (
        "Hola, me interesa el producto *{product_name}* (SKU: {sku}). "
        "¿Podría darme más información?"
    )

    # Si True, muestra base_price en el catálogo público.
    # Si False, CatalogProduct.base_price = None y el frontend no renderiza precio.
    catalog_show_prices: bool = True

    # Símbolo de moneda mostrado en el catálogo (no afecta lógica de precios).
    catalog_currency_symbol: str = "Bs."

    # URL base para construir URLs de imágenes subidas localmente.
    # En producción: "http://dominio.com" o "https://dominio.com"
    # En desarrollo: "http://localhost:8000"
    media_base_url: str = "http://localhost:8000"

    # Path local donde el backend guarda las imágenes subidas.
    # En Docker este path es el mountpoint del volumen compartido con nginx.
    media_local_path: str = "./media"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"


settings = Settings()
```

Agregar a `.env.example`:
```ini
# Catálogo público (Sprint 3)
WHATSAPP_CATALOG_PHONE=591XXXXXXXXX
WHATSAPP_MESSAGE_TEMPLATE=Hola, me interesa el producto *{product_name}* (SKU: {sku}). ¿Me da más información?
CATALOG_SHOW_PRICES=true
CATALOG_CURRENCY_SYMBOL=Bs.
MEDIA_BASE_URL=http://localhost:8000
MEDIA_LOCAL_PATH=./media
```

---

## 6. Puerto: CatalogRepositoryPort

Archivo: `backend/src/application/ports/repositories/catalog_repository_port.py`

```python
from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.models.catalog import CatalogCategory, CatalogProduct


class CatalogRepositoryPort(ABC):
    """
    Puerto de solo lectura para el catálogo público.
    Solo retorna productos con is_active=True AND show_in_catalog=True.
    Nunca expone wholesale_price ni datos operativos.
    """

    @abstractmethod
    async def list_catalog_products(
        self,
        category_slug: str | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 24,
    ) -> tuple[list[CatalogProduct], int]:
        """
        Retorna (productos, total).
        - category_slug: filtra por slug de categoría (None = todas)
        - search: búsqueda case-insensitive en name y description (None = sin filtro)
        - skip/limit: paginación
        Solo incluye productos activos con show_in_catalog=True.
        Las imágenes vienen ordenadas por sort_order ASC, is_primary DESC.
        """
        ...

    @abstractmethod
    async def get_catalog_product_by_sku(self, sku: str) -> CatalogProduct | None:
        """
        Retorna el producto completo con todas sus imágenes ordenadas.
        None si el producto no existe, no está activo o show_in_catalog=False.
        """
        ...

    @abstractmethod
    async def list_catalog_categories(self) -> list[CatalogCategory]:
        """
        Retorna categorías que tienen al menos un producto activo en catálogo,
        con product_count = cantidad de productos visibles por categoría.
        Ordenadas por name ASC.
        """
        ...

    @abstractmethod
    async def get_related_products(
        self,
        product_id: UUID,
        category_id: UUID,
        limit: int = 4,
    ) -> list[CatalogProduct]:
        """
        Retorna hasta `limit` productos de la misma categoría, excluyendo product_id.
        Solo activos con show_in_catalog=True.
        Ordenados por created_at DESC (los más nuevos primero).
        """
        ...
```

---

## 7. Puerto: ProductImageRepositoryPort

Archivo: `backend/src/application/ports/repositories/product_image_repository_port.py`

```python
from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.models.catalog import ProductImage


class ProductImageRepositoryPort(ABC):
    """Puerto para gestión de imágenes de producto (operaciones admin)."""

    @abstractmethod
    async def get_images_for_product(self, product_id: UUID) -> list[ProductImage]:
        """
        Retorna todas las imágenes del producto ordenadas por sort_order ASC.
        Lista vacía si el producto no tiene imágenes.
        """
        ...

    @abstractmethod
    async def add_image(self, image: ProductImage) -> ProductImage:
        """
        Persiste una nueva imagen. El llamador ya habrá guardado el archivo en disco.
        Retorna la imagen con id y created_at asignados.
        """
        ...

    @abstractmethod
    async def set_primary_image(self, product_id: UUID, image_id: UUID) -> None:
        """
        Marca image_id como is_primary=True y desmarca todas las demás del producto.
        Operación atómica en una sola transacción:
          UPDATE product_images SET is_primary=false WHERE product_id=$1
          UPDATE product_images SET is_primary=true  WHERE id=$2
        Lanza NotFoundError si image_id no existe o no pertenece a product_id.
        """
        ...

    @abstractmethod
    async def reorder_images(
        self, product_id: UUID, ordered_ids: list[UUID]
    ) -> None:
        """
        Reasigna sort_order según la posición en ordered_ids (índice 0 = sort_order 0).
        ordered_ids debe contener exactamente los IDs de todas las imágenes del producto.
        Lanza ValueError si la lista no coincide con las imágenes existentes.
        """
        ...

    @abstractmethod
    async def delete_image(self, image_id: UUID) -> ProductImage:
        """
        Elimina el registro de BD. Retorna la imagen eliminada para que el llamador
        pueda borrar el archivo físico de disco.
        Si la imagen eliminada era is_primary y quedan otras, promueve automáticamente
        la de menor sort_order como nueva primary.
        Lanza NotFoundError si image_id no existe.
        """
        ...
```

---

## 8. Endpoint de Subida de Imágenes (admin)

### 8.1 ORM Model

Archivo: `backend/src/infrastructure/database/orm_models/product_image_orm.py`

```python
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.base import Base


class ProductImageORM(Base):
    __tablename__ = "product_images"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    alt_text: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_product_images_product_id_sort", "product_id", "sort_order"),
        # El índice parcial uq_product_images_primary se crea en la migración
        # SQLAlchemy no lo declara aquí porque no soporta WHERE en UniqueConstraint
    )
```

### 8.2 Schemas Pydantic

Archivo: `backend/src/infrastructure/api/v1/schemas/product_image_schema.py`

```python
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ProductImageResponse(BaseModel):
    id: UUID
    product_id: UUID
    url: str
    alt_text: str | None
    sort_order: int
    is_primary: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ReorderImagesRequest(BaseModel):
    ordered_ids: list[UUID] = Field(
        ...,
        min_length=1,
        description="IDs de imágenes en el orden deseado (índice 0 = sort_order 0)",
    )
```

### 8.3 Endpoints FastAPI

Archivo: `backend/src/infrastructure/api/v1/endpoints/product_images.py`

```python
import os
import uuid
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from src.application.exceptions import NotFoundError
from src.application.ports.repositories.product_image_repository_port import ProductImageRepositoryPort
from src.application.ports.repositories.product_repository_port import ProductRepositoryPort
from src.config import settings
from src.dependencies import get_product_image_repo, get_product_repo
from src.domain.models.catalog import ProductImage
from src.infrastructure.api.v1.schemas.product_image_schema import (
    ProductImageResponse,
    ReorderImagesRequest,
)

router = APIRouter(prefix="/products/{product_id}/images", tags=["Imágenes de Producto"])

# Tipos MIME aceptados y su extensión correspondiente
ALLOWED_CONTENT_TYPES: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


def _validate_image(file: UploadFile) -> str:
    """Valida tipo MIME y retorna la extensión. Lanza HTTPException si es inválido."""
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Tipo de archivo no permitido: {file.content_type}. "
                   f"Aceptados: {', '.join(ALLOWED_CONTENT_TYPES)}",
        )
    return ALLOWED_CONTENT_TYPES[file.content_type]


async def _read_and_validate_size(file: UploadFile) -> bytes:
    """Lee el contenido y valida que no supere MAX_FILE_SIZE_BYTES."""
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Imagen demasiado grande. Máximo permitido: {MAX_FILE_SIZE_BYTES // (1024*1024)} MB",
        )
    return contents


def _build_media_url(product_id: UUID, filename: str) -> str:
    """Construye la URL pública de la imagen."""
    return f"{settings.media_base_url.rstrip('/')}/media/{product_id}/{filename}"


def _save_to_disk(product_id: UUID, filename: str, contents: bytes) -> Path:
    """Guarda el archivo en MEDIA_LOCAL_PATH/{product_id}/{filename}."""
    dest_dir = Path(settings.media_local_path) / str(product_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / filename
    dest_path.write_bytes(contents)
    return dest_path


@router.post(
    "",
    response_model=ProductImageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Subir imagen de producto",
    description=(
        "Sube una imagen (JPG, PNG o WebP, máx. 5 MB) y la asocia al producto. "
        "La imagen se guarda en `/media/{product_id}/` y la URL se persiste en BD. "
        "Si es la primera imagen del producto, se marca automáticamente como primary."
    ),
)
async def upload_product_image(
    product_id: UUID,
    file: UploadFile = File(..., description="Archivo de imagen (jpg/png/webp, máx. 5MB)"),
    alt_text: str | None = None,
    product_repo: ProductRepositoryPort = Depends(get_product_repo),
    image_repo: ProductImageRepositoryPort = Depends(get_product_image_repo),
):
    # Verificar que el producto existe
    product = await product_repo.get_by_id(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    extension = _validate_image(file)
    contents = await _read_and_validate_size(file)

    filename = f"{uuid.uuid4()}{extension}"
    _save_to_disk(product_id, filename, contents)
    url = _build_media_url(product_id, filename)

    # Determinar si será la primera imagen (auto-primary)
    existing = await image_repo.get_images_for_product(product_id)
    is_first = len(existing) == 0

    image = ProductImage(
        id=uuid.uuid4(),
        product_id=product_id,
        url=url,
        alt_text=alt_text,
        sort_order=len(existing),
        is_primary=is_first,
        created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
    )
    saved = await image_repo.add_image(image)
    return ProductImageResponse(
        id=saved.id,
        product_id=saved.product_id,
        url=saved.url,
        alt_text=saved.alt_text,
        sort_order=saved.sort_order,
        is_primary=saved.is_primary,
        created_at=saved.created_at,
    )


@router.get(
    "",
    response_model=list[ProductImageResponse],
    summary="Listar imágenes del producto",
)
async def list_product_images(
    product_id: UUID,
    image_repo: ProductImageRepositoryPort = Depends(get_product_image_repo),
):
    images = await image_repo.get_images_for_product(product_id)
    return [
        ProductImageResponse(
            id=img.id,
            product_id=img.product_id,
            url=img.url,
            alt_text=img.alt_text,
            sort_order=img.sort_order,
            is_primary=img.is_primary,
            created_at=img.created_at,
        )
        for img in images
    ]


@router.put(
    "/{image_id}/primary",
    response_model=ProductImageResponse,
    summary="Marcar imagen como principal",
    description="La imagen principal es la que aparece como thumbnail en el catálogo.",
)
async def set_primary_image(
    product_id: UUID,
    image_id: UUID,
    image_repo: ProductImageRepositoryPort = Depends(get_product_image_repo),
):
    try:
        await image_repo.set_primary_image(product_id, image_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    images = await image_repo.get_images_for_product(product_id)
    primary = next((img for img in images if img.id == image_id), None)
    if primary is None:
        raise HTTPException(status_code=404, detail="Imagen no encontrada tras actualizar")
    return ProductImageResponse(
        id=primary.id,
        product_id=primary.product_id,
        url=primary.url,
        alt_text=primary.alt_text,
        sort_order=primary.sort_order,
        is_primary=primary.is_primary,
        created_at=primary.created_at,
    )


@router.put(
    "/reorder",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Reordenar imágenes",
    description=(
        "Recibe la lista completa de IDs en el nuevo orden. "
        "El índice 0 de la lista corresponde a sort_order=0 (primera en la galería)."
    ),
)
async def reorder_images(
    product_id: UUID,
    body: ReorderImagesRequest,
    image_repo: ProductImageRepositoryPort = Depends(get_product_image_repo),
):
    try:
        await image_repo.reorder_images(product_id, body.ordered_ids)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete(
    "/{image_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar imagen",
    description="Elimina el registro de BD y el archivo físico de disco.",
)
async def delete_image(
    product_id: UUID,
    image_id: UUID,
    image_repo: ProductImageRepositoryPort = Depends(get_product_image_repo),
):
    try:
        deleted = await image_repo.delete_image(image_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Borrar archivo físico (best-effort — no falla el request si el archivo ya no existe)
    file_path = Path(deleted.url.replace(settings.media_base_url, settings.media_local_path))
    try:
        if file_path.exists():
            file_path.unlink()
    except OSError:
        pass  # Log en producción, no rompe el flujo
```

### 8.4 Registro en router y main.py

En `backend/src/infrastructure/api/v1/router.py`:
```python
from src.infrastructure.api.v1.endpoints.product_images import router as product_images_router
# ... imports existentes ...

api_router.include_router(product_images_router)
```

Agregar ruta estática para servir `/media/` en desarrollo. En `backend/src/main.py`:
```python
from fastapi.staticfiles import StaticFiles
import os

# Después de crear la app FastAPI:
media_path = settings.media_local_path
os.makedirs(media_path, exist_ok=True)
app.mount("/media", StaticFiles(directory=media_path), name="media")
```

Agregar a `backend/requirements.txt`: `python-multipart>=0.0.9` (requerido por FastAPI para `UploadFile`).

---

## 9. Endpoints Públicos de Catálogo

### 9.1 Schemas de respuesta del catálogo

Archivo: `backend/src/infrastructure/api/v1/schemas/catalog_schema.py`

```python
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class CatalogImageResponse(BaseModel):
    id: UUID
    url: str
    alt_text: str | None
    sort_order: int
    is_primary: bool

    model_config = {"from_attributes": True}


class CatalogProductResponse(BaseModel):
    """
    Respuesta pública. NUNCA incluir: wholesale_price, cost_price,
    quantity_on_hand, low_stock_threshold, sold_by.
    """
    id: UUID
    sku: str
    name: str
    description: str | None
    category_id: UUID
    category_name: str
    category_slug: str
    unit: str
    attributes: dict = Field(default_factory=dict)
    images: list[CatalogImageResponse] = Field(default_factory=list)
    base_price: Decimal | None = Field(
        None,
        description="Precio base. None si CATALOG_SHOW_PRICES=False en el servidor."
    )

    model_config = {"from_attributes": True}


class CatalogProductListResponse(BaseModel):
    items: list[CatalogProductResponse]
    total: int
    skip: int
    limit: int


class CatalogCategoryResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    description: str | None
    product_count: int

    model_config = {"from_attributes": True}
```

### 9.2 Router público

Archivo: `backend/src/infrastructure/api/v1/endpoints/catalog.py`

```python
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from src.application.ports.repositories.catalog_repository_port import CatalogRepositoryPort
from src.config import settings
from src.dependencies import get_catalog_repo
from src.infrastructure.api.v1.schemas.catalog_schema import (
    CatalogCategoryResponse,
    CatalogProductListResponse,
    CatalogProductResponse,
    CatalogImageResponse,
)

router = APIRouter(tags=["Catálogo Público"])


def _to_product_response(p) -> CatalogProductResponse:
    """Convierte CatalogProduct a schema de respuesta, aplicando CATALOG_SHOW_PRICES."""
    return CatalogProductResponse(
        id=p.id,
        sku=p.sku,
        name=p.name,
        description=p.description,
        category_id=p.category_id,
        category_name=p.category_name,
        category_slug=p.category_slug,
        unit=p.unit,
        attributes=p.attributes,
        images=[
            CatalogImageResponse(
                id=img.id,
                url=img.url,
                alt_text=img.alt_text,
                sort_order=img.sort_order,
                is_primary=img.is_primary,
            )
            for img in p.images
        ],
        base_price=p.base_price if settings.catalog_show_prices else None,
    )


@router.get(
    "/products",
    response_model=CatalogProductListResponse,
    summary="Listar productos del catálogo público",
    description=(
        "Lista paginada de productos activos y visibles en catálogo. "
        "No requiere autenticación. No expone precios mayoristas ni datos internos."
    ),
    responses={
        200: {
            "description": "Lista de productos",
            "content": {
                "application/json": {
                    "example": {
                        "items": [
                            {
                                "id": "550e8400-e29b-41d4-a716-446655440000",
                                "sku": "EQU-00001",
                                "name": "Montura Criolla Vaqueta",
                                "description": "Montura artesanal en cuero vaqueta curtido...",
                                "category_id": "...",
                                "category_name": "Equino",
                                "category_slug": "equino",
                                "unit": "unidad",
                                "attributes": {"leather_type": "vaqueta", "color": "natural"},
                                "images": [
                                    {
                                        "id": "...",
                                        "url": "http://localhost:8000/media/.../foto.webp",
                                        "alt_text": "Montura criolla vista lateral",
                                        "sort_order": 0,
                                        "is_primary": True,
                                    }
                                ],
                                "base_price": "1850.00",
                            }
                        ],
                        "total": 42,
                        "skip": 0,
                        "limit": 24,
                    }
                }
            },
        }
    },
)
async def list_catalog_products(
    category_slug: str | None = Query(None, description="Filtrar por slug de categoría"),
    search: str | None = Query(None, description="Búsqueda en nombre y descripción"),
    skip: int = Query(0, ge=0, description="Offset de paginación"),
    limit: int = Query(24, ge=1, le=100, description="Máximo de resultados (máx. 100)"),
    catalog_repo: CatalogRepositoryPort = Depends(get_catalog_repo),
):
    products, total = await catalog_repo.list_catalog_products(
        category_slug=category_slug,
        search=search,
        skip=skip,
        limit=limit,
    )
    return CatalogProductListResponse(
        items=[_to_product_response(p) for p in products],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/products/{sku}",
    response_model=CatalogProductResponse,
    summary="Detalle de producto por SKU",
    description=(
        "Retorna el detalle completo del producto incluyendo todas sus imágenes y atributos. "
        "404 si el producto no existe, no está activo o no está visible en catálogo."
    ),
    responses={
        200: {
            "description": "Detalle del producto",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "sku": "EQU-00001",
                        "name": "Montura Criolla Vaqueta",
                        "description": "Montura artesanal en cuero vaqueta curtido al vegetal...",
                        "category_id": "...",
                        "category_name": "Equino",
                        "category_slug": "equino",
                        "unit": "unidad",
                        "attributes": {
                            "leather_type": "vaqueta",
                            "color": "natural",
                            "talla": "universal",
                            "peso_kg": "8.5",
                        },
                        "images": [
                            {"id": "...", "url": "...", "alt_text": "Vista lateral", "sort_order": 0, "is_primary": True},
                            {"id": "...", "url": "...", "alt_text": "Vista frontal", "sort_order": 1, "is_primary": False},
                        ],
                        "base_price": "1850.00",
                    }
                }
            },
        },
        404: {"description": "Producto no encontrado o no visible en catálogo"},
    },
)
async def get_catalog_product(
    sku: str,
    catalog_repo: CatalogRepositoryPort = Depends(get_catalog_repo),
):
    product = await catalog_repo.get_catalog_product_by_sku(sku.upper())
    if product is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado en el catálogo")
    return _to_product_response(product)


@router.get(
    "/categories",
    response_model=list[CatalogCategoryResponse],
    summary="Categorías con productos en catálogo",
    description="Solo retorna categorías que tienen al menos un producto activo visible en catálogo.",
)
async def list_catalog_categories(
    catalog_repo: CatalogRepositoryPort = Depends(get_catalog_repo),
):
    categories = await catalog_repo.list_catalog_categories()
    return [
        CatalogCategoryResponse(
            id=cat.id,
            name=cat.name,
            slug=cat.slug,
            description=cat.description,
            product_count=cat.product_count,
        )
        for cat in categories
    ]


@router.get(
    "/products/{sku}/related",
    response_model=list[CatalogProductResponse],
    summary="Productos relacionados",
    description="Hasta 4 productos de la misma categoría, excluyendo el producto actual.",
)
async def get_related_products(
    sku: str,
    catalog_repo: CatalogRepositoryPort = Depends(get_catalog_repo),
):
    product = await catalog_repo.get_catalog_product_by_sku(sku.upper())
    if product is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    related = await catalog_repo.get_related_products(
        product_id=product.id,
        category_id=product.category_id,
        limit=4,
    )
    return [_to_product_response(p) for p in related]
```

### 9.3 Registro en main.py

```python
# En backend/src/main.py, DESPUÉS de include_router(api_router):
from src.infrastructure.api.v1.endpoints.catalog import router as catalog_router

# El router de catálogo NO pasa por AuditMiddleware porque es solo-lectura GET
# y se registra directamente en la app, no en api_router
app.include_router(catalog_router, prefix="/api/v1/catalog")
```

Agregar tag metadata en `_TAGS_METADATA`:
```python
{
    "name": "Catálogo Público",
    "description": "Endpoints públicos de la vitrina. Sin autenticación. Solo lectura. "
                   "Expone únicamente productos con `show_in_catalog=True` e `is_active=True`.",
},
```

### 9.4 Adaptador PostgreSQL: CatalogRepository

Archivo: `backend/src/infrastructure/adapters/postgres_repo/catalog_repository.py`

```python
from uuid import UUID

from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.application.ports.repositories.catalog_repository_port import CatalogRepositoryPort
from src.domain.models.catalog import CatalogCategory, CatalogProduct, ProductImage
from src.infrastructure.database.orm_models.category_orm import CategoryORM
from src.infrastructure.database.orm_models.product_image_orm import ProductImageORM
from src.infrastructure.database.orm_models.product_orm import ProductORM


class CatalogRepository(CatalogRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _base_filter(self):
        """Filtro base: activo y visible en catálogo."""
        return and_(ProductORM.is_active == True, ProductORM.show_in_catalog == True)

    def _orm_to_domain(self, orm: ProductORM, category: CategoryORM) -> CatalogProduct:
        images = [
            ProductImage(
                id=img.id,
                product_id=img.product_id,
                url=img.url,
                alt_text=img.alt_text,
                sort_order=img.sort_order,
                is_primary=img.is_primary,
                created_at=img.created_at,
            )
            for img in sorted(orm.images, key=lambda i: (i.sort_order, not i.is_primary))
        ]
        return CatalogProduct(
            id=orm.id,
            sku=orm.sku,
            name=orm.name,
            description=orm.description,
            category_id=orm.category_id,
            category_name=category.name,
            category_slug=category.slug,
            unit=orm.unit,
            attributes=orm.attributes or {},
            images=images,
            is_active=orm.is_active,
            show_in_catalog=orm.show_in_catalog,
            base_price=orm.base_price,
        )

    async def list_catalog_products(
        self,
        category_slug: str | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 24,
    ) -> tuple[list[CatalogProduct], int]:
        stmt = (
            select(ProductORM, CategoryORM)
            .join(CategoryORM, ProductORM.category_id == CategoryORM.id)
            .options(selectinload(ProductORM.images))
            .where(self._base_filter())
        )
        if category_slug:
            stmt = stmt.where(CategoryORM.slug == category_slug)
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                or_(
                    ProductORM.name.ilike(pattern),
                    ProductORM.description.ilike(pattern),
                )
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self._session.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(ProductORM.name.asc()).offset(skip).limit(limit)
        rows = (await self._session.execute(stmt)).all()

        products = [self._orm_to_domain(row.ProductORM, row.CategoryORM) for row in rows]
        return products, total

    async def get_catalog_product_by_sku(self, sku: str) -> CatalogProduct | None:
        stmt = (
            select(ProductORM, CategoryORM)
            .join(CategoryORM, ProductORM.category_id == CategoryORM.id)
            .options(selectinload(ProductORM.images))
            .where(ProductORM.sku == sku)
            .where(self._base_filter())
        )
        row = (await self._session.execute(stmt)).first()
        if row is None:
            return None
        return self._orm_to_domain(row.ProductORM, row.CategoryORM)

    async def list_catalog_categories(self) -> list[CatalogCategory]:
        stmt = (
            select(CategoryORM, func.count(ProductORM.id).label("product_count"))
            .join(
                ProductORM,
                and_(
                    ProductORM.category_id == CategoryORM.id,
                    ProductORM.is_active == True,
                    ProductORM.show_in_catalog == True,
                ),
                isouter=True,
            )
            .group_by(CategoryORM.id)
            .having(func.count(ProductORM.id) > 0)
            .order_by(CategoryORM.name.asc())
        )
        rows = (await self._session.execute(stmt)).all()
        return [
            CatalogCategory(
                id=row.CategoryORM.id,
                name=row.CategoryORM.name,
                slug=row.CategoryORM.slug,
                description=row.CategoryORM.description,
                product_count=row.product_count,
            )
            for row in rows
        ]

    async def get_related_products(
        self, product_id: UUID, category_id: UUID, limit: int = 4
    ) -> list[CatalogProduct]:
        stmt = (
            select(ProductORM, CategoryORM)
            .join(CategoryORM, ProductORM.category_id == CategoryORM.id)
            .options(selectinload(ProductORM.images))
            .where(self._base_filter())
            .where(ProductORM.category_id == category_id)
            .where(ProductORM.id != product_id)
            .order_by(ProductORM.created_at.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).all()
        return [self._orm_to_domain(row.ProductORM, row.CategoryORM) for row in rows]
```

---

## 10. Frontend — Rutas y Componentes

### 10.1 Estructura de rutas

```
frontend/src/app/
  catalogo/
    layout.tsx              — layout público (header + footer, sin sidebar)
    page.tsx                — vitrina principal con filtros y grid de productos
    loading.tsx             — skeleton de carga
    [sku]/
      page.tsx              — detalle del producto (Server Component para SEO)
      loading.tsx
    categoria/
      [slug]/
        page.tsx            — productos filtrados por categoría
```

### 10.2 Tipos TypeScript para catálogo

Archivo: `frontend/src/types/catalog.ts`

```typescript
export interface CatalogImage {
  id: string;
  url: string;
  alt_text: string | null;
  sort_order: number;
  is_primary: boolean;
}

export interface CatalogProduct {
  id: string;
  sku: string;
  name: string;
  description: string | null;
  category_id: string;
  category_name: string;
  category_slug: string;
  unit: string;
  attributes: Record<string, unknown>;
  images: CatalogImage[];
  base_price: number | null;  // null si CATALOG_SHOW_PRICES=false en el servidor
}

export interface CatalogProductListResponse {
  items: CatalogProduct[];
  total: number;
  skip: number;
  limit: number;
}

export interface CatalogCategory {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  product_count: number;
}

export interface ProductImageUpload {
  id: string;
  product_id: string;
  url: string;
  alt_text: string | null;
  sort_order: number;
  is_primary: boolean;
  created_at: string;
}
```

### 10.3 Services TypeScript

Archivo: `frontend/src/services/catalog.service.ts`

```typescript
// Las llamadas al catálogo van directamente a la API pública — sin auth header
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export const catalogService = {
  listProducts: async (params?: {
    category_slug?: string;
    search?: string;
    skip?: number;
    limit?: number;
  }): Promise<CatalogProductListResponse> => {
    const url = new URL(`${API_URL}/catalog/products`);
    if (params?.category_slug) url.searchParams.set("category_slug", params.category_slug);
    if (params?.search) url.searchParams.set("search", params.search);
    if (params?.skip != null) url.searchParams.set("skip", String(params.skip));
    if (params?.limit != null) url.searchParams.set("limit", String(params.limit));

    const res = await fetch(url.toString(), { next: { revalidate: 60 } });
    if (!res.ok) throw new Error(`Error ${res.status} al cargar catálogo`);
    return res.json();
  },

  getProductBySku: async (sku: string): Promise<CatalogProduct> => {
    const res = await fetch(`${API_URL}/catalog/products/${sku}`, {
      next: { revalidate: 60 },
    });
    if (res.status === 404) throw new Error("Producto no encontrado");
    if (!res.ok) throw new Error(`Error ${res.status}`);
    return res.json();
  },

  listCategories: async (): Promise<CatalogCategory[]> => {
    const res = await fetch(`${API_URL}/catalog/categories`, {
      next: { revalidate: 300 },
    });
    if (!res.ok) throw new Error(`Error ${res.status} al cargar categorías`);
    return res.json();
  },

  getRelatedProducts: async (sku: string): Promise<CatalogProduct[]> => {
    const res = await fetch(`${API_URL}/catalog/products/${sku}/related`, {
      next: { revalidate: 60 },
    });
    if (!res.ok) return [];
    return res.json();
  },
};
```

Archivo: `frontend/src/services/product-images.service.ts`

```typescript
import { api } from "@/lib/api";
import type { ProductImageUpload } from "@/types/catalog";

export const productImagesService = {
  list: async (productId: string): Promise<ProductImageUpload[]> => {
    const { data } = await api.get<ProductImageUpload[]>(
      `/products/${productId}/images`
    );
    return data;
  },

  upload: async (
    productId: string,
    file: File,
    altText?: string
  ): Promise<ProductImageUpload> => {
    const formData = new FormData();
    formData.append("file", file);
    if (altText) formData.append("alt_text", altText);
    const { data } = await api.post<ProductImageUpload>(
      `/products/${productId}/images`,
      formData,
      { headers: { "Content-Type": "multipart/form-data" } }
    );
    return data;
  },

  setPrimary: async (
    productId: string,
    imageId: string
  ): Promise<ProductImageUpload> => {
    const { data } = await api.put<ProductImageUpload>(
      `/products/${productId}/images/${imageId}/primary`
    );
    return data;
  },

  reorder: async (
    productId: string,
    orderedIds: string[]
  ): Promise<void> => {
    await api.put(`/products/${productId}/images/reorder`, {
      ordered_ids: orderedIds,
    });
  },

  delete: async (productId: string, imageId: string): Promise<void> => {
    await api.delete(`/products/${productId}/images/${imageId}`);
  },
};
```

### 10.4 Layout del Catálogo

Archivo: `frontend/src/app/catalogo/layout.tsx`

```tsx
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: {
    template: "%s | Black Horse Talabartería",
    default: "Catálogo | Black Horse Talabartería",
  },
  description:
    "Artículos de cuero artesanales: monturas, riendas, accesorios equinos y bovinos. Fabricación propia en Bolivia.",
};

export default function CatalogoLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen flex flex-col bg-brand-50">
      {/* Header público */}
      <header className="bg-brand-800 text-white shadow-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            {/* Logo — reemplazar src con logo real */}
            <div className="w-10 h-10 bg-brand-500 rounded-full flex items-center justify-center text-white font-bold text-lg">
              BH
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight">Black Horse</h1>
              <p className="text-brand-200 text-xs">Talabartería artesanal</p>
            </div>
          </div>
          <div className="text-right hidden sm:block">
            <p className="text-brand-200 text-sm">Contacto</p>
            <a
              href="https://wa.me/591XXXXXXXXX"
              className="text-green-400 font-semibold text-sm hover:text-green-300 transition-colors"
              target="_blank"
              rel="noopener noreferrer"
            >
              +591 XX XXX XXXX
            </a>
          </div>
        </div>
        {/* Barra de navegación de categorías */}
        <nav className="bg-brand-700 border-t border-brand-600">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex gap-6 py-2 overflow-x-auto scrollbar-hide text-sm">
              <a
                href="/catalogo"
                className="text-brand-100 hover:text-white whitespace-nowrap transition-colors"
              >
                Todo el catálogo
              </a>
              {/* Las categorías se cargan dinámicamente en cada página */}
            </div>
          </div>
        </nav>
      </header>

      {/* Contenido principal */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>

      {/* Footer */}
      <footer className="bg-brand-900 text-brand-300 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-8">
            <div>
              <h3 className="text-white font-semibold mb-2">Black Horse Talabartería</h3>
              <p className="text-sm">Artículos de cuero artesanales desde 1985.</p>
            </div>
            <div>
              <h3 className="text-white font-semibold mb-2">Dirección</h3>
              <p className="text-sm">Av. Principal 123, Santa Cruz, Bolivia</p>
            </div>
            <div>
              <h3 className="text-white font-semibold mb-2">Contacto</h3>
              <a
                href="https://wa.me/591XXXXXXXXX"
                className="text-green-400 hover:text-green-300 text-sm block"
                target="_blank"
                rel="noopener noreferrer"
              >
                WhatsApp: +591 XX XXX XXXX
              </a>
            </div>
          </div>
          <p className="text-center text-brand-500 text-xs mt-8">
            © {new Date().getFullYear()} Black Horse Talabartería. Todos los derechos reservados.
          </p>
        </div>
      </footer>
    </div>
  );
}
```

### 10.5 Componente WhatsAppButton

Archivo: `frontend/src/components/catalog/WhatsAppButton.tsx`

```tsx
"use client";

interface WhatsAppButtonProps {
  productName: string;
  sku: string;
  phoneNumber: string;        // "591XXXXXXXXX" sin +
  messageTemplate: string;    // "Hola, me interesa {product_name} (SKU: {sku})"
  variant?: "fixed" | "inline";
}

function buildWhatsAppUrl(
  phone: string,
  template: string,
  productName: string,
  sku: string
): string {
  const message = template
    .replace("{product_name}", productName)
    .replace("{sku}", sku);
  return `https://wa.me/${phone}?text=${encodeURIComponent(message)}`;
}

export function WhatsAppButton({
  productName,
  sku,
  phoneNumber,
  messageTemplate,
  variant = "inline",
}: WhatsAppButtonProps) {
  const url = buildWhatsAppUrl(phoneNumber, messageTemplate, productName, sku);

  if (variant === "fixed") {
    return (
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        className="fixed bottom-6 right-6 z-50 bg-green-500 hover:bg-green-600 text-white rounded-full p-4 shadow-lg flex items-center gap-2 transition-all sm:hidden"
        aria-label="Consultar por WhatsApp"
      >
        <WhatsAppIcon className="w-6 h-6" />
      </a>
    );
  }

  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-3 bg-green-500 hover:bg-green-600 text-white font-semibold text-lg px-8 py-4 rounded-xl shadow-md transition-colors w-full justify-center sm:w-auto"
      aria-label={`Consultar sobre ${productName} por WhatsApp`}
    >
      <WhatsAppIcon className="w-6 h-6" />
      Consultar por WhatsApp
    </a>
  );
}

function WhatsAppIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
    </svg>
  );
}
```

### 10.6 Componente ProductCard

Archivo: `frontend/src/components/catalog/ProductCard.tsx`

```tsx
import Image from "next/image";
import Link from "next/link";
import type { CatalogProduct } from "@/types/catalog";
import { formatCurrency } from "@/lib/formatters";

interface ProductCardProps {
  product: CatalogProduct;
  showPrice: boolean;
  currencySymbol: string;
}

const LEATHER_PLACEHOLDER =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='400' viewBox='0 0 400 400'%3E%3Crect width='400' height='400' fill='%23d4a574'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' font-family='serif' font-size='60' fill='%23a0522d'%3E🧵%3C/text%3E%3C/svg%3E";

export function ProductCard({ product, showPrice, currencySymbol }: ProductCardProps) {
  const primaryImage =
    product.images.find((img) => img.is_primary) ?? product.images[0] ?? null;

  return (
    <div className="bg-white rounded-2xl shadow-sm hover:shadow-md transition-shadow overflow-hidden group border border-brand-100">
      {/* Imagen */}
      <div className="relative aspect-square overflow-hidden bg-brand-50">
        <Image
          src={primaryImage?.url ?? LEATHER_PLACEHOLDER}
          alt={primaryImage?.alt_text ?? product.name}
          fill
          className="object-cover group-hover:scale-105 transition-transform duration-300"
          sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
        />
        {/* Badge de categoría */}
        <span className="absolute top-3 left-3 bg-brand-800/80 text-white text-xs font-medium px-2 py-1 rounded-full backdrop-blur-sm">
          {product.category_name}
        </span>
        {/* Hover: botón WhatsApp */}
        <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
          <a
            href={`https://wa.me/${process.env.NEXT_PUBLIC_WHATSAPP_PHONE}?text=${encodeURIComponent(
              `Hola, me interesa ${product.name} (SKU: ${product.sku})`
            )}`}
            target="_blank"
            rel="noopener noreferrer"
            className="bg-green-500 hover:bg-green-600 text-white text-sm font-semibold px-4 py-2 rounded-full"
            onClick={(e) => e.stopPropagation()}
          >
            Consultar
          </a>
        </div>
      </div>

      {/* Info */}
      <div className="p-4">
        <h3 className="font-semibold text-brand-900 text-sm leading-tight line-clamp-2 mb-1">
          {product.name}
        </h3>
        <p className="text-brand-400 text-xs mb-3">SKU: {product.sku}</p>

        {showPrice && product.base_price != null && (
          <p className="text-brand-700 font-bold text-lg">
            {currencySymbol} {formatCurrency(product.base_price).replace("Bs.", "").trim()}
          </p>
        )}

        <Link
          href={`/catalogo/${product.sku}`}
          className="mt-3 block text-center bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium py-2 px-4 rounded-lg transition-colors"
        >
          Ver detalle
        </Link>
      </div>
    </div>
  );
}
```

### 10.7 Página Principal del Catálogo

Archivo: `frontend/src/app/catalogo/page.tsx`

```tsx
import type { Metadata } from "next";
import { Suspense } from "react";
import { catalogService } from "@/services/catalog.service";
import { ProductCard } from "@/components/catalog/ProductCard";
import { CategoryFilter } from "@/components/catalog/CategoryFilter";
import { CatalogSearch } from "@/components/catalog/CatalogSearch";

export const metadata: Metadata = {
  title: "Catálogo de Productos",
  description:
    "Explora nuestra colección de artículos de cuero artesanales: monturas, riendas, accesorios equinos, bovinos y marroquinería.",
  openGraph: {
    title: "Catálogo | Black Horse Talabartería",
    description: "Artículos de cuero artesanales desde Bolivia.",
    type: "website",
  },
};

interface PageProps {
  searchParams: {
    categoria?: string;
    buscar?: string;
    pagina?: string;
  };
}

const LIMIT = 24;
const SHOW_PRICE = process.env.CATALOG_SHOW_PRICES !== "false";
const CURRENCY = process.env.CATALOG_CURRENCY_SYMBOL ?? "Bs.";

// Server Component — fetch en el servidor para SEO
export default async function CatalogoPage({ searchParams }: PageProps) {
  const page = Number(searchParams.pagina ?? 1);
  const skip = (page - 1) * LIMIT;

  const [{ items: products, total }, categories] = await Promise.all([
    catalogService.listProducts({
      category_slug: searchParams.categoria,
      search: searchParams.buscar,
      skip,
      limit: LIMIT,
    }),
    catalogService.listCategories(),
  ]);

  const totalPages = Math.ceil(total / LIMIT);

  return (
    <div className="flex flex-col lg:flex-row gap-8">
      {/* Sidebar filtros */}
      <aside className="w-full lg:w-64 flex-shrink-0">
        <div className="bg-white rounded-2xl shadow-sm border border-brand-100 p-5 sticky top-4">
          <h2 className="font-bold text-brand-900 mb-4 text-lg">Filtros</h2>
          {/* Búsqueda de texto */}
          <Suspense>
            <CatalogSearch />
          </Suspense>
          {/* Filtro por categoría */}
          <div className="mt-6">
            <h3 className="font-semibold text-brand-700 mb-3 text-sm uppercase tracking-wide">
              Categorías
            </h3>
            <CategoryFilter
              categories={categories}
              activeSlug={searchParams.categoria}
            />
          </div>
        </div>
      </aside>

      {/* Grid de productos */}
      <section className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-6">
          <p className="text-brand-500 text-sm">
            {total} {total === 1 ? "producto" : "productos"}
            {searchParams.categoria && ` en ${searchParams.categoria}`}
          </p>
        </div>

        {products.length === 0 ? (
          <div className="text-center py-20 text-brand-400">
            <p className="text-2xl mb-2">No hay productos disponibles</p>
            <p className="text-sm">Intenta con otros filtros o categorías.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-6">
            {products.map((product) => (
              <ProductCard
                key={product.id}
                product={product}
                showPrice={SHOW_PRICE}
                currencySymbol={CURRENCY}
              />
            ))}
          </div>
        )}

        {/* Paginación clásica con links (mejor para SEO que infinite scroll) */}
        {totalPages > 1 && (
          <nav className="flex justify-center gap-2 mt-10" aria-label="Paginación">
            {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
              <a
                key={p}
                href={`/catalogo?${new URLSearchParams({
                  ...(searchParams.categoria ? { categoria: searchParams.categoria } : {}),
                  ...(searchParams.buscar ? { buscar: searchParams.buscar } : {}),
                  pagina: String(p),
                })}`}
                className={`w-10 h-10 flex items-center justify-center rounded-lg text-sm font-medium transition-colors ${
                  p === page
                    ? "bg-brand-600 text-white"
                    : "bg-white text-brand-700 border border-brand-200 hover:bg-brand-50"
                }`}
                aria-current={p === page ? "page" : undefined}
              >
                {p}
              </a>
            ))}
          </nav>
        )}
      </section>
    </div>
  );
}
```

**Decisión de paginación**: se usa paginación clásica con links `<a href>` en lugar de infinite scroll porque:
1. Los links son indexables por Google y los bots de WhatsApp
2. El usuario puede compartir una URL con `?pagina=3` y llegar exactamente a esa página
3. Server Components de Next.js 14 renderizan directamente desde `searchParams` — no requiere estado del cliente

### 10.8 Componentes de Apoyo

Archivo: `frontend/src/components/catalog/CategoryFilter.tsx`

```tsx
import Link from "next/link";
import type { CatalogCategory } from "@/types/catalog";

interface CategoryFilterProps {
  categories: CatalogCategory[];
  activeSlug?: string;
}

export function CategoryFilter({ categories, activeSlug }: CategoryFilterProps) {
  return (
    <ul className="space-y-1">
      <li>
        <Link
          href="/catalogo"
          className={`flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors ${
            !activeSlug
              ? "bg-brand-100 text-brand-900 font-semibold"
              : "text-brand-600 hover:bg-brand-50"
          }`}
        >
          <span>Todos</span>
        </Link>
      </li>
      {categories.map((cat) => (
        <li key={cat.id}>
          <Link
            href={`/catalogo?categoria=${cat.slug}`}
            className={`flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors ${
              activeSlug === cat.slug
                ? "bg-brand-100 text-brand-900 font-semibold"
                : "text-brand-600 hover:bg-brand-50"
            }`}
          >
            <span>{cat.name}</span>
            <span className="bg-brand-200 text-brand-700 text-xs px-2 py-0.5 rounded-full">
              {cat.product_count}
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
```

Archivo: `frontend/src/components/catalog/CatalogSearch.tsx`

```tsx
"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useTransition } from "react";

export function CatalogSearch() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();

  const handleSearch = useCallback(
    (value: string) => {
      const params = new URLSearchParams(searchParams.toString());
      if (value) {
        params.set("buscar", value);
      } else {
        params.delete("buscar");
      }
      params.delete("pagina"); // reset paginación al buscar
      startTransition(() => {
        router.push(`/catalogo?${params.toString()}`);
      });
    },
    [router, searchParams]
  );

  return (
    <div className="relative">
      <input
        type="search"
        placeholder="Buscar productos..."
        defaultValue={searchParams.get("buscar") ?? ""}
        onChange={(e) => handleSearch(e.target.value)}
        className={`w-full border border-brand-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400 bg-brand-50 ${
          isPending ? "opacity-70" : ""
        }`}
        aria-label="Buscar en el catálogo"
      />
    </div>
  );
}
```

### 10.9 Página de Detalle del Producto

Archivo: `frontend/src/app/catalogo/[sku]/page.tsx`

```tsx
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Image from "next/image";
import { catalogService } from "@/services/catalog.service";
import { WhatsAppButton } from "@/components/catalog/WhatsAppButton";
import { ImageGallery } from "@/components/catalog/ImageGallery";
import { ProductCard } from "@/components/catalog/ProductCard";
import { formatCurrency } from "@/lib/formatters";

const SHOW_PRICE = process.env.CATALOG_SHOW_PRICES !== "false";
const CURRENCY = process.env.CATALOG_CURRENCY_SYMBOL ?? "Bs.";
const WA_PHONE = process.env.NEXT_PUBLIC_WHATSAPP_PHONE ?? "591XXXXXXXXX";
const WA_TEMPLATE =
  process.env.NEXT_PUBLIC_WHATSAPP_TEMPLATE ??
  "Hola, me interesa el producto *{product_name}* (SKU: {sku}). ¿Podría darme más información?";

interface PageProps {
  params: { sku: string };
}

// generateMetadata se ejecuta en el servidor — el scraper de WhatsApp ve los og:tags
export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  try {
    const product = await catalogService.getProductBySku(params.sku.toUpperCase());
    const primaryImage =
      product.images.find((img) => img.is_primary) ?? product.images[0];

    return {
      title: product.name,
      description:
        product.description ??
        `${product.name} — ${product.category_name}. Artículo de cuero artesanal.`,
      openGraph: {
        title: `${product.name} | Black Horse Talabartería`,
        description:
          product.description ??
          `${product.name} — ${product.category_name}. Artículo de cuero artesanal.`,
        type: "product",
        images: primaryImage
          ? [
              {
                url: primaryImage.url,
                width: 800,
                height: 800,
                alt: primaryImage.alt_text ?? product.name,
              },
            ]
          : [],
        url: `https://dominio.com/catalogo/${product.sku}`,
      },
    };
  } catch {
    return { title: "Producto no encontrado" };
  }
}

// Server Component — toda la data se resuelve en el servidor
export default async function ProductoDetallePage({ params }: PageProps) {
  let product;
  try {
    product = await catalogService.getProductBySku(params.sku.toUpperCase());
  } catch {
    notFound();
  }

  const relatedProducts = await catalogService.getRelatedProducts(product.sku);

  // Renderizar atributos del JSONB de forma legible
  const attributeLabels: Record<string, string> = {
    leather_type: "Tipo de cuero",
    color: "Color",
    size: "Talla / Medida",
    weight_kg: "Peso (kg)",
    talla: "Talla",
    acabado: "Acabado",
    origin: "Origen",
  };

  const attributeEntries = Object.entries(product.attributes).filter(
    ([, v]) => v !== null && v !== undefined && v !== ""
  );

  return (
    <>
      {/* Botón flotante WhatsApp en mobile */}
      <WhatsAppButton
        productName={product.name}
        sku={product.sku}
        phoneNumber={WA_PHONE}
        messageTemplate={WA_TEMPLATE}
        variant="fixed"
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
        {/* Galería de imágenes */}
        <ImageGallery images={product.images} productName={product.name} />

        {/* Información del producto */}
        <div className="flex flex-col gap-6">
          {/* Breadcrumb */}
          <nav className="text-sm text-brand-400">
            <a href="/catalogo" className="hover:text-brand-600 transition-colors">
              Catálogo
            </a>
            {" / "}
            <a
              href={`/catalogo?categoria=${product.category_slug}`}
              className="hover:text-brand-600 transition-colors"
            >
              {product.category_name}
            </a>
            {" / "}
            <span className="text-brand-700">{product.name}</span>
          </nav>

          {/* Nombre y SKU */}
          <div>
            <span className="bg-brand-100 text-brand-700 text-xs font-medium px-2 py-1 rounded-full">
              {product.category_name}
            </span>
            <h1 className="text-3xl font-bold text-brand-900 mt-3 leading-tight">
              {product.name}
            </h1>
            <p className="text-brand-400 text-sm mt-1">SKU: {product.sku}</p>
          </div>

          {/* Precio */}
          {SHOW_PRICE && product.base_price != null && (
            <div className="bg-brand-50 border border-brand-200 rounded-xl p-4">
              <p className="text-brand-500 text-sm mb-1">Precio</p>
              <p className="text-4xl font-bold text-brand-800">
                {CURRENCY}{" "}
                {formatCurrency(product.base_price).replace("Bs.", "").trim()}
              </p>
              <p className="text-brand-400 text-xs mt-1">
                Precio en {product.unit}. Consultar por cantidad.
              </p>
            </div>
          )}

          {/* Descripción */}
          {product.description && (
            <div>
              <h2 className="font-semibold text-brand-800 mb-2">Descripción</h2>
              <p className="text-brand-600 leading-relaxed">{product.description}</p>
            </div>
          )}

          {/* Tabla de atributos */}
          {attributeEntries.length > 0 && (
            <div>
              <h2 className="font-semibold text-brand-800 mb-3">Características</h2>
              <table className="w-full text-sm border-collapse">
                <tbody>
                  {attributeEntries.map(([key, value]) => (
                    <tr key={key} className="border-b border-brand-100">
                      <td className="py-2 pr-4 text-brand-500 font-medium w-40">
                        {attributeLabels[key] ?? key}
                      </td>
                      <td className="py-2 text-brand-800">{String(value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Botón WhatsApp principal */}
          <div className="hidden sm:block">
            <WhatsAppButton
              productName={product.name}
              sku={product.sku}
              phoneNumber={WA_PHONE}
              messageTemplate={WA_TEMPLATE}
              variant="inline"
            />
          </div>

          <p className="text-brand-400 text-xs">
            Horario de atención: Lunes a Sábado 8:00 – 18:00 hs.
          </p>
        </div>
      </div>

      {/* Productos relacionados */}
      {relatedProducts.length > 0 && (
        <section className="mt-16">
          <h2 className="text-2xl font-bold text-brand-900 mb-6">
            También te puede interesar
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {relatedProducts.map((p) => (
              <ProductCard
                key={p.id}
                product={p}
                showPrice={SHOW_PRICE}
                currencySymbol={CURRENCY}
              />
            ))}
          </div>
        </section>
      )}
    </>
  );
}
```

### 10.10 Galería de Imágenes (Client Component)

Archivo: `frontend/src/components/catalog/ImageGallery.tsx`

```tsx
"use client";

import { useState } from "react";
import Image from "next/image";
import type { CatalogImage } from "@/types/catalog";

const PLACEHOLDER =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='800' height='800' viewBox='0 0 800 800'%3E%3Crect width='800' height='800' fill='%23d4a574'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' font-size='120' fill='%23a0522d'%3E🧵%3C/text%3E%3C/svg%3E";

interface ImageGalleryProps {
  images: CatalogImage[];
  productName: string;
}

export function ImageGallery({ images, productName }: ImageGalleryProps) {
  const [activeIndex, setActiveIndex] = useState(0);

  const sorted = [...images].sort((a, b) => {
    if (a.is_primary && !b.is_primary) return -1;
    if (!a.is_primary && b.is_primary) return 1;
    return a.sort_order - b.sort_order;
  });

  const activeImage = sorted[activeIndex] ?? null;

  return (
    <div className="flex flex-col gap-4">
      {/* Imagen principal */}
      <div className="relative aspect-square rounded-2xl overflow-hidden bg-brand-50 border border-brand-100">
        <Image
          src={activeImage?.url ?? PLACEHOLDER}
          alt={activeImage?.alt_text ?? productName}
          fill
          priority
          className="object-cover"
          sizes="(max-width: 1024px) 100vw, 50vw"
        />
      </div>

      {/* Miniaturas */}
      {sorted.length > 1 && (
        <div className="flex gap-3 overflow-x-auto pb-1">
          {sorted.map((img, index) => (
            <button
              key={img.id}
              onClick={() => setActiveIndex(index)}
              className={`relative flex-shrink-0 w-20 h-20 rounded-lg overflow-hidden border-2 transition-all ${
                index === activeIndex
                  ? "border-brand-600 shadow-md"
                  : "border-brand-200 opacity-70 hover:opacity-100"
              }`}
              aria-label={`Ver imagen ${index + 1}`}
              aria-current={index === activeIndex}
            >
              <Image
                src={img.url}
                alt={img.alt_text ?? `${productName} imagen ${index + 1}`}
                fill
                className="object-cover"
                sizes="80px"
              />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
```

### 10.11 Página de Categoría

Archivo: `frontend/src/app/catalogo/categoria/[slug]/page.tsx`

```tsx
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { catalogService } from "@/services/catalog.service";
import { ProductCard } from "@/components/catalog/ProductCard";

const SHOW_PRICE = process.env.CATALOG_SHOW_PRICES !== "false";
const CURRENCY = process.env.CATALOG_CURRENCY_SYMBOL ?? "Bs.";

interface PageProps {
  params: { slug: string };
  searchParams: { pagina?: string };
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const categories = await catalogService.listCategories();
  const cat = categories.find((c) => c.slug === params.slug);
  if (!cat) return { title: "Categoría no encontrada" };
  return {
    title: `${cat.name} — Catálogo`,
    description: cat.description ?? `Productos de ${cat.name} en cuero artesanal.`,
    openGraph: { title: `${cat.name} | Black Horse Talabartería` },
  };
}

export default async function CategoriaPage({ params, searchParams }: PageProps) {
  const LIMIT = 24;
  const page = Number(searchParams.pagina ?? 1);
  const skip = (page - 1) * LIMIT;

  const [{ items: products, total }, categories] = await Promise.all([
    catalogService.listProducts({ category_slug: params.slug, skip, limit: LIMIT }),
    catalogService.listCategories(),
  ]);

  const category = categories.find((c) => c.slug === params.slug);
  if (!category) notFound();

  return (
    <div>
      <div className="mb-8">
        <nav className="text-sm text-brand-400 mb-2">
          <a href="/catalogo" className="hover:text-brand-600">Catálogo</a> / {category.name}
        </nav>
        <h1 className="text-3xl font-bold text-brand-900">{category.name}</h1>
        {category.description && (
          <p className="text-brand-500 mt-2">{category.description}</p>
        )}
        <p className="text-brand-400 text-sm mt-1">{total} productos</p>
      </div>

      {products.length === 0 ? (
        <p className="text-center text-brand-400 py-20">No hay productos en esta categoría.</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {products.map((p) => (
            <ProductCard key={p.id} product={p} showPrice={SHOW_PRICE} currencySymbol={CURRENCY} />
          ))}
        </div>
      )}
    </div>
  );
}
```

### 10.12 Admin — Toggle y Galería en ProductForm

El componente `ProductForm.tsx` existente en `frontend/src/components/products/ProductForm.tsx` requiere dos cambios:

**a) Campo `show_in_catalog` en el formulario**

Agregar al schema Zod en `frontend/src/schemas/product.schema.ts`:
```typescript
show_in_catalog: z.boolean().default(false),
```

Agregar en `UpdateProductInput` en `frontend/src/types/index.ts`:
```typescript
show_in_catalog?: boolean;
```

En el JSX del formulario, después del campo `is_active`:
```tsx
{/* Solo mostrar para productos terminados o para reventa */}
{(productType === "finished_product" || productType === "resale") && (
  <div className="flex items-center gap-3 p-3 bg-brand-50 rounded-lg border border-brand-200">
    <input
      type="checkbox"
      id="show_in_catalog"
      {...register("show_in_catalog")}
      className="w-4 h-4 accent-brand-600"
    />
    <label htmlFor="show_in_catalog" className="text-sm text-brand-700 cursor-pointer">
      <span className="font-medium">Mostrar en catálogo público</span>
      <span className="block text-brand-400 text-xs">
        El producto será visible en la vitrina pública sin autenticación
      </span>
    </label>
  </div>
)}
```

**b) Sección de galería de imágenes**

Crear `frontend/src/components/products/ImageGalleryAdmin.tsx`:

```tsx
"use client";

import { useCallback, useRef, useState } from "react";
import Image from "next/image";
import { productImagesService } from "@/services/product-images.service";
import type { ProductImageUpload } from "@/types/catalog";

interface ImageGalleryAdminProps {
  productId: string;
  initialImages: ProductImageUpload[];
}

export function ImageGalleryAdmin({ productId, initialImages }: ImageGalleryAdminProps) {
  const [images, setImages] = useState<ProductImageUpload[]>(
    [...initialImages].sort((a, b) => a.sort_order - b.sort_order)
  );
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Drag-and-drop para reordenar
  const [dragging, setDragging] = useState<string | null>(null);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    if (files.length === 0) return;
    setUploading(true);
    setError(null);
    try {
      const uploaded: ProductImageUpload[] = [];
      for (const file of files) {
        const img = await productImagesService.upload(productId, file);
        uploaded.push(img);
      }
      setImages((prev) => [...prev, ...uploaded]);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al subir imagen");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleSetPrimary = async (imageId: string) => {
    try {
      await productImagesService.setPrimary(productId, imageId);
      setImages((prev) =>
        prev.map((img) => ({ ...img, is_primary: img.id === imageId }))
      );
    } catch {
      setError("Error al establecer imagen principal");
    }
  };

  const handleDelete = async (imageId: string) => {
    if (!confirm("¿Eliminar esta imagen?")) return;
    try {
      await productImagesService.delete(productId, imageId);
      setImages((prev) => prev.filter((img) => img.id !== imageId));
    } catch {
      setError("Error al eliminar imagen");
    }
  };

  const handleDragStart = (imageId: string) => setDragging(imageId);
  const handleDragOver = (e: React.DragEvent, targetId: string) => {
    e.preventDefault();
    if (!dragging || dragging === targetId) return;
    setImages((prev) => {
      const from = prev.findIndex((i) => i.id === dragging);
      const to = prev.findIndex((i) => i.id === targetId);
      const next = [...prev];
      const [item] = next.splice(from, 1);
      next.splice(to, 0, item);
      return next.map((img, idx) => ({ ...img, sort_order: idx }));
    });
  };
  const handleDrop = async () => {
    setDragging(null);
    try {
      await productImagesService.reorder(
        productId,
        images.map((img) => img.id)
      );
    } catch {
      setError("Error al reordenar imágenes");
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-brand-800">Galería de imágenes</h3>
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          className="text-sm bg-brand-600 hover:bg-brand-700 text-white px-3 py-1.5 rounded-lg disabled:opacity-60 transition-colors"
        >
          {uploading ? "Subiendo..." : "+ Agregar imágenes"}
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          multiple
          onChange={handleUpload}
          className="hidden"
        />
      </div>

      {error && (
        <p className="text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg px-3 py-2">
          {error}
        </p>
      )}

      <p className="text-xs text-brand-400">
        Arrastra para reordenar. Formatos: JPG, PNG, WebP. Máx. 5 MB por imagen.
      </p>

      {images.length === 0 ? (
        <div
          className="border-2 border-dashed border-brand-200 rounded-xl p-8 text-center text-brand-400 text-sm cursor-pointer hover:border-brand-400 transition-colors"
          onClick={() => fileInputRef.current?.click()}
        >
          No hay imágenes. Haz clic para subir.
        </div>
      ) : (
        <div className="grid grid-cols-3 sm:grid-cols-4 gap-3">
          {images.map((img) => (
            <div
              key={img.id}
              draggable
              onDragStart={() => handleDragStart(img.id)}
              onDragOver={(e) => handleDragOver(e, img.id)}
              onDrop={handleDrop}
              className={`relative group rounded-xl overflow-hidden border-2 cursor-move transition-all ${
                img.is_primary ? "border-brand-500 shadow-md" : "border-brand-100"
              } ${dragging === img.id ? "opacity-50" : ""}`}
            >
              <div className="aspect-square relative">
                <Image
                  src={img.url}
                  alt={img.alt_text ?? "Imagen de producto"}
                  fill
                  className="object-cover"
                  sizes="120px"
                />
              </div>
              {img.is_primary && (
                <span className="absolute top-1 left-1 bg-brand-600 text-white text-xs px-1.5 py-0.5 rounded">
                  Principal
                </span>
              )}
              {/* Overlay de acciones */}
              <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col items-center justify-center gap-1 p-1">
                {!img.is_primary && (
                  <button
                    type="button"
                    onClick={() => handleSetPrimary(img.id)}
                    className="text-xs bg-brand-500 text-white px-2 py-1 rounded w-full"
                  >
                    Principal
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => handleDelete(img.id)}
                  className="text-xs bg-red-500 text-white px-2 py-1 rounded w-full"
                >
                  Eliminar
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

---

## 11. Configuración de Next.js para Imágenes

Archivo: `frontend/next.config.js`

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  images: {
    remotePatterns: [
      // Backend local en desarrollo
      {
        protocol: "http",
        hostname: "localhost",
        port: "8000",
        pathname: "/media/**",
      },
      // Backend en Docker (nombre del servicio)
      {
        protocol: "http",
        hostname: "backend",
        port: "8000",
        pathname: "/media/**",
      },
      // Producción — reemplazar con dominio real
      {
        protocol: "https",
        hostname: "dominio.com",
        pathname: "/media/**",
      },
    ],
  },
};

module.exports = nextConfig;
```

Agregar a `frontend/.env.local` (desarrollo):
```ini
NEXT_PUBLIC_WHATSAPP_PHONE=591XXXXXXXXX
NEXT_PUBLIC_WHATSAPP_TEMPLATE=Hola, me interesa el producto *{product_name}* (SKU: {sku}). ¿Podría darme más información?
CATALOG_SHOW_PRICES=true
CATALOG_CURRENCY_SYMBOL=Bs.
```

---

## 12. Criterios de Aceptación

- [ ] La migración 004 se aplica sin errores sobre una BD con datos existentes de sprints 1 y 2
- [ ] La tabla `product_images` no puede tener dos filas con `is_primary=true` para el mismo `product_id` (error de constraint al intentarlo)
- [ ] `DELETE` en `products` elimina en cascada todas las filas de `product_images` del producto
- [ ] `POST /api/v1/products/{id}/images` acepta JPG, PNG y WebP de hasta 5 MB
- [ ] `POST /api/v1/products/{id}/images` rechaza con 415 un archivo PDF o GIF
- [ ] `POST /api/v1/products/{id}/images` rechaza con 413 un archivo mayor a 5 MB
- [ ] La primera imagen subida a un producto se marca automáticamente como `is_primary=true`
- [ ] `PUT /api/v1/products/{id}/images/{img_id}/primary` actualiza correctamente y la imagen anterior pierde `is_primary`
- [ ] `PUT /api/v1/products/{id}/images/reorder` actualiza `sort_order` de todas las imágenes en el orden enviado
- [ ] `DELETE /api/v1/products/{id}/images/{img_id}` elimina el archivo físico de disco y el registro de BD
- [ ] `GET /api/v1/catalog/products` no incluye `wholesale_price` en ningún objeto de la respuesta
- [ ] `GET /api/v1/catalog/products` no incluye productos con `is_active=false`
- [ ] `GET /api/v1/catalog/products` no incluye productos con `show_in_catalog=false`
- [ ] `GET /api/v1/catalog/products?category_slug=equino` retorna solo productos de categoría Equino
- [ ] `GET /api/v1/catalog/products?search=montura` retorna resultados con "montura" en nombre o descripción
- [ ] `GET /api/v1/catalog/products/{sku}` retorna 404 para un producto con `show_in_catalog=false` aunque exista
- [ ] `GET /api/v1/catalog/categories` retorna solo categorías con al menos un producto visible, con `product_count` correcto
- [ ] La URL `/catalogo` carga sin autenticación desde un navegador en incógnito
- [ ] La URL `/catalogo/EQU-00001` genera `<meta property="og:image">` con la URL de la imagen principal en el HTML inicial (verificable con `curl`)
- [ ] El botón "Consultar por WhatsApp" en la página de detalle genera la URL correcta con el mensaje codificado
- [ ] El toggle "Mostrar en catálogo" en el dashboard actualiza `show_in_catalog` vía `PUT /api/v1/products/{id}`
- [ ] Las imágenes en el catálogo usan `next/image` con `sizes` apropiados (verificar en Network que se sirven tamaños optimizados)
- [ ] La galería de miniaturas en la página de detalle permite cambiar la imagen principal visible
- [ ] Las imágenes subidas persisten al reiniciar los contenedores Docker (verificar con volumen montado)

---

## 13. Deployment Notes

### 13.1 Volumen compartido para imágenes en Docker Compose

Agregar a `docker-compose.yml`:

```yaml
services:
  backend:
    # ... configuración existente ...
    volumes:
      - media_data:/app/media   # /app/media es MEDIA_LOCAL_PATH en el contenedor
    environment:
      MEDIA_LOCAL_PATH: /app/media
      MEDIA_BASE_URL: http://localhost:80  # nginx sirve en el puerto 80

  nginx:
    # ... configuración existente ...
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - media_data:/media:ro    # nginx sirve /media/ en modo solo-lectura

volumes:
  postgres_data:
  pgadmin_data:
  media_data:        # NUEVO — compartido entre backend y nginx
```

Agregar a `nginx/nginx.conf` (en el bloque `server`):
```nginx
# Servir imágenes subidas directamente desde nginx (sin pasar por FastAPI)
location /media/ {
    alias /media/;
    expires 30d;
    add_header Cache-Control "public, immutable";
    add_header X-Content-Type-Options nosniff;
    # Permitir acceso desde el frontend público
    add_header Access-Control-Allow-Origin "*";
}
```

### 13.2 Alternativa S3 (documentación, no implementada en Sprint 3)

Si el volumen local no escala, se puede migrar sin cambiar el esquema de BD:

1. Agregar variables: `MEDIA_S3_BUCKET`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`
2. Instalar `boto3`
3. Reemplazar `_save_to_disk()` por un `s3.put_object()` en el endpoint de upload
4. Cambiar `_build_media_url()` para retornar `https://{bucket}.s3.amazonaws.com/{key}`
5. El campo `url` en `product_images` ya almacena la URL completa — sin cambios en BD

### 13.3 URL del catálogo compartible

La URL que el negocio comparte por WhatsApp:
- Catálogo general: `http://dominio.com/catalogo`
- Categoría específica: `http://dominio.com/catalogo?categoria=equino`
- Producto específico: `http://dominio.com/catalogo/EQU-00001`

Para producción, configurar `NEXT_PUBLIC_API_URL=https://dominio.com/api/v1` y `MEDIA_BASE_URL=https://dominio.com` en las variables de entorno del servidor.

---

## 14. Testing

### 14.1 Tests de endpoints de catálogo

Archivo: `backend/tests/integration/test_catalog_endpoints.py`

```python
"""Tests de integración para los endpoints públicos del catálogo."""
import pytest
from httpx import AsyncClient

from src.main import app


@pytest.mark.asyncio
async def test_catalog_products_excludes_private_fields(
    async_client: AsyncClient, create_visible_product
):
    """El endpoint público nunca debe exponer wholesale_price ni campos internos."""
    response = await async_client.get("/api/v1/catalog/products")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data

    for item in data["items"]:
        assert "wholesale_price" not in item, "wholesale_price no debe aparecer en catálogo"
        assert "cost_price" not in item, "cost_price no debe aparecer en catálogo"
        assert "quantity_on_hand" not in item, "stock no debe aparecer en catálogo"
        assert "low_stock_threshold" not in item


@pytest.mark.asyncio
async def test_catalog_only_shows_visible_products(
    async_client: AsyncClient,
    create_visible_product,
    create_hidden_product,   # show_in_catalog=False
    create_inactive_product, # is_active=False
):
    response = await async_client.get("/api/v1/catalog/products")
    assert response.status_code == 200
    skus = {item["sku"] for item in response.json()["items"]}
    assert create_visible_product.sku in skus
    assert create_hidden_product.sku not in skus
    assert create_inactive_product.sku not in skus


@pytest.mark.asyncio
async def test_catalog_filter_by_category(async_client: AsyncClient, create_visible_product):
    response = await async_client.get(
        "/api/v1/catalog/products",
        params={"category_slug": "equino"}
    )
    assert response.status_code == 200
    for item in response.json()["items"]:
        assert item["category_slug"] == "equino"


@pytest.mark.asyncio
async def test_catalog_pagination(async_client: AsyncClient, create_many_visible_products):
    """Verifica que skip/limit funcionen correctamente."""
    r1 = await async_client.get("/api/v1/catalog/products", params={"skip": 0, "limit": 2})
    r2 = await async_client.get("/api/v1/catalog/products", params={"skip": 2, "limit": 2})
    ids_page1 = {item["id"] for item in r1.json()["items"]}
    ids_page2 = {item["id"] for item in r2.json()["items"]}
    assert ids_page1.isdisjoint(ids_page2), "Las páginas no deben solaparse"


@pytest.mark.asyncio
async def test_catalog_product_detail_404_for_hidden(
    async_client: AsyncClient, create_hidden_product
):
    response = await async_client.get(
        f"/api/v1/catalog/products/{create_hidden_product.sku}"
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_catalog_categories_with_product_count(
    async_client: AsyncClient, create_visible_product
):
    response = await async_client.get("/api/v1/catalog/categories")
    assert response.status_code == 200
    for cat in response.json():
        assert "product_count" in cat
        assert cat["product_count"] > 0, "Solo categorías con productos visibles"
```

### 14.2 Tests de upload de imagen

Archivo: `backend/tests/integration/test_product_images.py`

```python
import io
import pytest
from httpx import AsyncClient
from PIL import Image as PILImage  # pip install pillow (solo en tests)


def _make_jpeg_bytes(size: tuple = (100, 100)) -> bytes:
    """Genera un JPEG mínimo válido en memoria."""
    buf = io.BytesIO()
    PILImage.new("RGB", size, color=(139, 69, 19)).save(buf, format="JPEG")
    return buf.getvalue()


def _make_large_file_bytes() -> bytes:
    """Genera un buffer de 6 MB (supera el límite de 5 MB)."""
    return b"x" * (6 * 1024 * 1024)


@pytest.mark.asyncio
async def test_upload_valid_jpeg(async_client: AsyncClient, create_product):
    jpeg_bytes = _make_jpeg_bytes()
    response = await async_client.post(
        f"/api/v1/products/{create_product.id}/images",
        files={"file": ("foto.jpg", jpeg_bytes, "image/jpeg")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["url"].startswith("http")
    assert data["url"].endswith(".jpg")
    assert data["is_primary"] is True  # primera imagen → automáticamente primary


@pytest.mark.asyncio
async def test_upload_invalid_type_rejected(async_client: AsyncClient, create_product):
    response = await async_client.post(
        f"/api/v1/products/{create_product.id}/images",
        files={"file": ("doc.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert response.status_code == 415


@pytest.mark.asyncio
async def test_upload_oversized_file_rejected(async_client: AsyncClient, create_product):
    large_bytes = _make_large_file_bytes()
    response = await async_client.post(
        f"/api/v1/products/{create_product.id}/images",
        files={"file": ("grande.jpg", large_bytes, "image/jpeg")},
    )
    assert response.status_code == 413


@pytest.mark.asyncio
async def test_set_primary_updates_correctly(async_client: AsyncClient, create_product):
    jpeg = _make_jpeg_bytes()
    r1 = await async_client.post(
        f"/api/v1/products/{create_product.id}/images",
        files={"file": ("foto1.jpg", jpeg, "image/jpeg")},
    )
    r2 = await async_client.post(
        f"/api/v1/products/{create_product.id}/images",
        files={"file": ("foto2.jpg", jpeg, "image/jpeg")},
    )
    img1_id = r1.json()["id"]
    img2_id = r2.json()["id"]

    # La primera es primary por defecto; marcar la segunda como primary
    r = await async_client.put(
        f"/api/v1/products/{create_product.id}/images/{img2_id}/primary"
    )
    assert r.status_code == 200
    assert r.json()["is_primary"] is True

    # Listar imágenes y verificar que solo la segunda es primary
    images_r = await async_client.get(f"/api/v1/products/{create_product.id}/images")
    images = {img["id"]: img for img in images_r.json()}
    assert images[img1_id]["is_primary"] is False
    assert images[img2_id]["is_primary"] is True
```

### 14.3 Test de generación de URL de WhatsApp

Archivo: `frontend/src/__tests__/whatsapp-url.test.ts`

```typescript
// Test unitario puro — no requiere entorno de browser
describe("WhatsApp URL generation", () => {
  function buildUrl(phone: string, template: string, name: string, sku: string): string {
    const message = template
      .replace("{product_name}", name)
      .replace("{sku}", sku);
    return `https://wa.me/${phone}?text=${encodeURIComponent(message)}`;
  }

  it("codifica correctamente caracteres especiales en el mensaje", () => {
    const url = buildUrl(
      "591XXXXXXXXX",
      "Hola, me interesa *{product_name}* (SKU: {sku})",
      "Montura Criolla",
      "EQU-00001"
    );
    expect(url).toContain("wa.me/591XXXXXXXXX");
    expect(url).toContain(encodeURIComponent("Montura Criolla"));
    expect(url).toContain(encodeURIComponent("EQU-00001"));
    // Los * de Markdown deben estar codificados
    expect(url).toContain("%2A");
    // El espacio no debe aparecer sin codificar
    expect(url).not.toContain(" ");
  });

  it("sustituye correctamente ambos placeholders", () => {
    const url = buildUrl(
      "5491123456789",
      "{product_name} - {sku}",
      "Cinturón",
      "ACC-00042"
    );
    expect(url).not.toContain("{product_name}");
    expect(url).not.toContain("{sku}");
    expect(url).toContain(encodeURIComponent("Cinturón"));
    expect(url).toContain(encodeURIComponent("ACC-00042"));
  });

  it("el número de teléfono no lleva + en la URL", () => {
    const url = buildUrl("591XXXXXXXXX", "Hola", "Prod", "SKU-1");
    expect(url).toMatch(/wa\.me\/591/);
    expect(url).not.toContain("+");
  });
});
```

Ejecutar con: `cd frontend && npm test -- whatsapp-url`

