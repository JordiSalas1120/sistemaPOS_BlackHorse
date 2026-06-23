from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from src.domain.models.enums import ProductType
from src.domain.models.product import Product


@dataclass
class WorkshopProductDTO:
    id: UUID
    sku: str
    name: str
    product_type: str
    category_id: UUID
    base_price: Decimal
    unit: str
    is_active: bool
    show_in_catalog: bool
    cost_price: Decimal | None = None
    wholesale_price: Decimal | None = None
    description: str | None = None
    quantity_on_hand: Decimal | None = None

    @classmethod
    def from_product(cls, p: Product) -> "WorkshopProductDTO":
        return cls(
            id=p.id,
            sku=p.sku,
            name=p.name,
            product_type=p.product_type,
            category_id=p.category_id,
            base_price=p.base_price,
            unit=p.unit,
            is_active=p.is_active,
            show_in_catalog=p.show_in_catalog,
            cost_price=p.cost_price,
            wholesale_price=p.wholesale_price,
            description=p.description,
        )


@dataclass
class WorkshopProductListDTO:
    items: list[WorkshopProductDTO]
    total: int
    skip: int
    limit: int
    product_type: ProductType
