from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from src.domain.models.enums import MovementType


@dataclass
class AdjustStockDTO:
    product_id: UUID
    quantity_delta: Decimal          # positivo = entrada, negativo = salida
    movement_type: MovementType
    actor: str
    notes: str | None = None
    reference_id: UUID | None = None


@dataclass
class UpdateThresholdDTO:
    product_id: UUID
    low_stock_threshold: Decimal


@dataclass
class InventoryDTO:
    product_id: UUID
    product_sku: str
    product_name: str
    quantity_on_hand: Decimal
    low_stock_threshold: Decimal
    is_low_stock: bool


@dataclass
class MovementDTO:
    id: UUID
    product_id: UUID
    movement_type: str
    quantity_delta: Decimal
    quantity_before: Decimal
    quantity_after: Decimal
    created_by: str
    created_at: datetime
    notes: str | None
