from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from src.domain.models.enums import ProductType, ProductUnit


class CategoryResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    description: str | None = None


class ProductCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    sku: str | None = Field(None, max_length=50)  # None = auto-generado
    category_id: UUID
    base_price: Decimal = Field(..., gt=0)
    unit: ProductUnit = ProductUnit.UNIT
    description: str | None = None
    wholesale_price: Decimal | None = Field(None, gt=0)
    image_url: str | None = None
    attributes: dict = Field(default_factory=dict)
    low_stock_threshold: Decimal = Field(Decimal("5"), ge=0)
    product_type: ProductType = ProductType.RESALE
    show_in_catalog: bool = False
    cost_price: Decimal | None = Field(None, gt=0)

    model_config = {
        "json_schema_extra": {
            "example": {
                "sku": "SIL-001",
                "name": "Silla vaquera cuero plena flor",
                "category_id": "uuid-aqui",
                "base_price": "45000.00",
                "unit": "unidad",
                "wholesale_price": "38000.00",
                "low_stock_threshold": "3",
            }
        }
    }


class ProductUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    category_id: UUID | None = None
    base_price: Decimal | None = Field(None, gt=0)
    wholesale_price: Decimal | None = Field(None, gt=0)
    unit: ProductUnit | None = None
    image_url: str | None = None
    attributes: dict | None = None
    is_active: bool | None = None
    product_type: ProductType | None = None
    show_in_catalog: bool | None = None
    cost_price: Decimal | None = Field(None, gt=0)


class ProductResponse(BaseModel):
    id: UUID
    sku: str
    name: str
    category_id: UUID
    category_name: str
    base_price: Decimal
    wholesale_price: Decimal | None = None
    unit: str
    description: str | None = None
    image_url: str | None = None
    attributes: dict
    is_active: bool
    quantity_on_hand: Decimal | None = None
    product_type: str = "resale"
    show_in_catalog: bool = False
    cost_price: Decimal | None = None


class ProductListResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    skip: int
    limit: int
