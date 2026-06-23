from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from src.domain.models.enums import MovementType


@dataclass
class Inventory:
    id: UUID
    product_id: UUID
    quantity_on_hand: Decimal
    low_stock_threshold: Decimal
    updated_at: datetime
    last_restocked_at: datetime | None = None

    def is_low_stock(self) -> bool:
        return self.quantity_on_hand <= self.low_stock_threshold

    def is_out_of_stock(self) -> bool:
        return self.quantity_on_hand <= Decimal("0")

    def can_fulfill(self, quantity: Decimal) -> bool:
        return self.quantity_on_hand >= quantity


@dataclass
class InventoryMovement:
    id: UUID
    product_id: UUID
    movement_type: MovementType
    quantity_delta: Decimal       # positivo = entrada, negativo = salida
    quantity_before: Decimal
    quantity_after: Decimal
    created_by: str
    created_at: datetime
    reference_id: UUID | None = None
    notes: str | None = None
