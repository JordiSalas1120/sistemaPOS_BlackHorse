from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from src.domain.models.enums import ProductionOrderStatus


# ── Input DTOs ────────────────────────────────────────────────────────────────

@dataclass
class CreateProductionOrderDTO:
    bom_id: UUID
    quantity_to_produce: Decimal
    produced_by: str
    notes: str | None = None


@dataclass
class CompleteProductionOrderDTO:
    quantity_produced: Decimal
    notes: str | None = None


@dataclass
class CancelProductionOrderDTO:
    reason: str


# ── Output DTOs ───────────────────────────────────────────────────────────────

@dataclass
class ProductionOrderItemDTO:
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


@dataclass
class ProductionOrderDTO:
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
    created_at: datetime
    updated_at: datetime
    estimated_cost_per_unit: Decimal
    unit_cost_snapshot: Decimal | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None
    notes: str | None = None
    items: list[ProductionOrderItemDTO] = field(default_factory=list)


@dataclass
class ProductionOrderListDTO:
    items: list[ProductionOrderDTO]
    total: int
    skip: int
    limit: int


# ── Helper de mapeo (compartido entre use cases) ──────────────────────────────

def _to_dto(
    order,
    items: list,
    material_info: dict | None = None,
    finished_product_name: str = "",
    finished_product_sku: str = "",
) -> ProductionOrderDTO:
    """
    Construye el DTO de salida.

    material_info: mapa opcional material_id → (sku, name) para enriquecer los ítems.
    """
    material_info = material_info or {}
    item_dtos = [
        ProductionOrderItemDTO(
            id=i.id,
            order_id=i.order_id,
            material_id=i.material_id,
            material_sku=material_info.get(i.material_id, ("", ""))[0],
            material_name=material_info.get(i.material_id, ("", ""))[1],
            quantity_required=i.quantity_required,
            quantity_consumed=i.quantity_consumed,
            unit_cost_snapshot=i.unit_cost_snapshot,
            subtotal_cost=i.subtotal_cost,
            notes=i.notes,
        )
        for i in items
    ]

    # Poblar order.items para que calculate_cost_per_unit refleje el estimado real
    order.items = items
    estimated = (
        order.calculate_cost_per_unit()
        if items
        else (order.unit_cost_snapshot or Decimal("0"))
    )

    return ProductionOrderDTO(
        id=order.id,
        order_number=order.order_number,
        bom_id=order.bom_id,
        finished_product_id=order.finished_product_id,
        finished_product_name=finished_product_name,
        finished_product_sku=finished_product_sku,
        quantity_to_produce=order.quantity_to_produce,
        quantity_produced=order.quantity_produced,
        status=order.status,
        produced_by=order.produced_by,
        created_at=order.created_at,
        updated_at=order.updated_at,
        estimated_cost_per_unit=estimated,
        unit_cost_snapshot=order.unit_cost_snapshot,
        started_at=order.started_at,
        completed_at=order.completed_at,
        cancelled_at=order.cancelled_at,
        notes=order.notes,
        items=item_dtos,
    )
