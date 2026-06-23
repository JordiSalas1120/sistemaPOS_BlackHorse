from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from src.domain.models.enums import MovementType


class AdjustStockRequest(BaseModel):
    product_id: UUID
    quantity_delta: Decimal = Field(..., description="Positivo = entrada, negativo = salida")
    movement_type: MovementType
    notes: str | None = None
    reference_id: UUID | None = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "product_id": "uuid-aqui",
                "quantity_delta": "10",
                "movement_type": "purchase",
                "notes": "Compra a proveedor Rodríguez",
            }
        }
    }


class MovementResponse(BaseModel):
    id: UUID
    product_id: UUID
    movement_type: str
    quantity_delta: Decimal
    quantity_before: Decimal
    quantity_after: Decimal
    created_by: str
    created_at: datetime
    notes: str | None = None


class InventoryItemResponse(BaseModel):
    product_id: UUID
    product_sku: str
    product_name: str
    quantity_on_hand: Decimal
    low_stock_threshold: Decimal
    is_low_stock: bool
