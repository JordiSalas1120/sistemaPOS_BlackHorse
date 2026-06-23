from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from src.domain.models.enums import ClientType, DiscountType, PriceRuleType


@dataclass
class PriceRule:
    id: UUID
    name: str
    rule_type: PriceRuleType
    discount_type: DiscountType
    discount_value: Decimal       # 15.00 = 15% o $15 fijos según discount_type
    priority: int
    is_active: bool
    created_at: datetime
    client_type_trigger: ClientType | None = None
    category_id: UUID | None = None
    product_id: UUID | None = None
    min_quantity: Decimal | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None

    def is_valid_now(self, now: datetime) -> bool:
        if not self.is_active:
            return False
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        return True

    def applies_to_client(self, client_type: ClientType) -> bool:
        if self.client_type_trigger is None:
            return True
        return self.client_type_trigger == client_type

    def applies_to_quantity(self, quantity: Decimal) -> bool:
        if self.min_quantity is None:
            return True
        return quantity >= self.min_quantity
