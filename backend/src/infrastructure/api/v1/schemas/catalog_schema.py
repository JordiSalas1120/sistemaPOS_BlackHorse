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
        description="Precio base. None si CATALOG_SHOW_PRICES=False en el servidor.",
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
