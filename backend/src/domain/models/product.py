from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from src.domain.models.enums import ProductType, ProductUnit


@dataclass
class Category:
    id: UUID
    name: str
    slug: str
    created_at: datetime
    description: str | None = None


@dataclass
class Product:
    id: UUID
    sku: str
    name: str
    category_id: UUID
    base_price: Decimal
    unit: ProductUnit
    attributes: dict          # JSONB: {"leather_type": "vaqueta", "size": "90cm", ...}
    is_active: bool
    created_at: datetime
    updated_at: datetime
    description: str | None = None
    wholesale_price: Decimal | None = None
    image_url: str | None = None
    product_type: ProductType = ProductType.RESALE
    show_in_catalog: bool = False
    cost_price: Decimal | None = None

    def get_effective_wholesale_price(self) -> Decimal:
        """Retorna el precio mayorista explícito si existe, sino el precio base."""
        return self.wholesale_price if self.wholesale_price is not None else self.base_price
