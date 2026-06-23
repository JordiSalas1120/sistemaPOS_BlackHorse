from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from src.domain.models.enums import ProductionOrderStatus


# ── Request schemas ───────────────────────────────────────────────────────────

class CreateProductionOrderRequest(BaseModel):
    bom_id: UUID
    quantity_to_produce: Decimal = Field(..., gt=0, description="Unidades a fabricar")
    produced_by: str = Field(..., min_length=1, max_length=100, description="Nombre del artífice/operario")
    notes: str | None = Field(None, max_length=1000)

    model_config = {
        "json_schema_extra": {
            "example": {
                "bom_id": "550e8400-e29b-41d4-a716-446655440000",
                "quantity_to_produce": "5",
                "produced_by": "Juan Artesano",
                "notes": "Lote urgente para feria"
            }
        }
    }


class CompleteProductionOrderRequest(BaseModel):
    quantity_produced: Decimal = Field(
        ..., gt=0, description="Cantidad efectivamente producida (puede ser menor a la planificada)"
    )
    notes: str | None = Field(None, max_length=1000, description="Observaciones del completado")

    model_config = {
        "json_schema_extra": {
            "example": {
                "quantity_produced": "5",
                "notes": "Sin inconvenientes"
            }
        }
    }


class CancelProductionOrderRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=500, description="Motivo de la cancelación")

    model_config = {
        "json_schema_extra": {
            "example": {"reason": "Se agotó el cuero antes de iniciar la producción"}
        }
    }


# ── Response schemas ──────────────────────────────────────────────────────────

class ProductionOrderItemResponse(BaseModel):
    id: UUID
    order_id: UUID
    material_id: UUID
    material_sku: str
    material_name: str
    quantity_required: Decimal
    quantity_consumed: Decimal
    unit_cost_snapshot: Decimal
    subtotal_cost: Decimal
    notes: str | None = None


class ProductionOrderResponse(BaseModel):
    id: UUID
    order_number: str
    bom_id: UUID
    finished_product_id: UUID
    finished_product_name: str
    finished_product_sku: str
    quantity_to_produce: Decimal
    quantity_produced: Decimal
    status: ProductionOrderStatus
    produced_by: str
    estimated_cost_per_unit: Decimal
    unit_cost_snapshot: Decimal | None
    started_at: datetime | None
    completed_at: datetime | None
    cancelled_at: datetime | None
    created_at: datetime
    updated_at: datetime
    notes: str | None
    items: list[ProductionOrderItemResponse] = Field(default_factory=list)


class ProductionOrderListResponse(BaseModel):
    items: list[ProductionOrderResponse]
    total: int
    skip: int
    limit: int
