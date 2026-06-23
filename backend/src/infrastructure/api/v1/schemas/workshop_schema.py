from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class WorkshopProductResponse(BaseModel):
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


class WorkshopProductListResponse(BaseModel):
    items: list[WorkshopProductResponse]
    total: int
    skip: int
    limit: int
    product_type: str
