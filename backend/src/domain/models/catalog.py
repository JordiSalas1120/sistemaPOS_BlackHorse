from dataclasses import dataclass
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
