from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from src.domain.models.enums import PaymentType, SaleStatus, SaleType


class SaleItemInputSchema(BaseModel):
    product_id: UUID
    quantity: Decimal = Field(..., gt=0)


class CreateSaleRequest(BaseModel):
    items: list[SaleItemInputSchema] = Field(..., min_length=1)
    payment_type: PaymentType
    sale_type: SaleType = SaleType.RETAIL
    client_id: UUID | None = None
    notes: str | None = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "items": [{"product_id": "uuid-aqui", "quantity": "2"}],
                "payment_type": "cash",
                "sale_type": "retail",
                "client_id": None,
            }
        }
    }


class SaleItemResponse(BaseModel):
    id: UUID
    sale_id: UUID
    product_id: UUID
    product_sku: str
    product_name: str
    quantity: Decimal
    unit_price: Decimal
    discount_amount: Decimal
    subtotal: Decimal


class SaleResponse(BaseModel):
    id: UUID
    sale_number: str
    sale_type: str
    status: str
    payment_type: str
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal
    total: Decimal
    sold_by: str
    created_at: datetime
    updated_at: datetime
    items: list[SaleItemResponse] = Field(default_factory=list)
    client_id: UUID | None = None
    notes: str | None = None


class SaleListResponse(BaseModel):
    items: list[SaleResponse]
    total: int
    skip: int
    limit: int
