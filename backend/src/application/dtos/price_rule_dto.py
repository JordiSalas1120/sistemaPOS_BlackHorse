from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from src.domain.models.enums import ClientType, DiscountType, PriceRuleType


@dataclass
class CreatePriceRuleDTO:
    name: str
    rule_type: PriceRuleType
    discount_type: DiscountType
    discount_value: Decimal
    priority: int = 0
    client_type_trigger: ClientType | None = None
    category_id: UUID | None = None
    product_id: UUID | None = None
    min_quantity: Decimal | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None


@dataclass
class PriceRuleDTO:
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
