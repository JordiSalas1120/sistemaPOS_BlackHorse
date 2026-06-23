from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from src.domain.models.enums import ClientType, DiscountType, PriceRuleType


class PriceRuleCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    rule_type: PriceRuleType
    discount_type: DiscountType
    discount_value: Decimal = Field(..., gt=0)
    priority: int = Field(0, ge=0)
    client_type_trigger: ClientType | None = None
    category_id: UUID | None = None
    product_id: UUID | None = None
    min_quantity: Decimal | None = Field(None, gt=0)
    valid_from: datetime | None = None
    valid_until: datetime | None = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Descuento mayorista 15%",
                "rule_type": "client_type",
                "discount_type": "percentage",
                "discount_value": "15",
                "priority": 10,
                "client_type_trigger": "wholesale",
            }
        }
    }


class PriceRuleResponse(BaseModel):
    id: UUID
    name: str
    rule_type: str
    discount_type: str
    discount_value: Decimal
    priority: int
    is_active: bool
    created_at: datetime
    client_type_trigger: str | None = None
    category_id: UUID | None = None
    product_id: UUID | None = None
    min_quantity: Decimal | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
