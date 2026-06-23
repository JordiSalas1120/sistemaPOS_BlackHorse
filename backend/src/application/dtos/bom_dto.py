from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from src.domain.models.bom import BOM, BOMItem


@dataclass
class BOMItemInputDTO:
    """DTO de entrada para una línea de receta."""
    material_id: UUID
    quantity_required: Decimal
    scrap_factor: Decimal = Decimal("0")
    notes: str | None = None


@dataclass
class CreateBOMDTO:
    output_quantity: Decimal
    items: list[BOMItemInputDTO]
    labor_minutes: int | None = None
    notes: str | None = None


@dataclass
class UpdateBOMDTO:
    output_quantity: Decimal | None = None
    labor_minutes: int | None = None
    notes: str | None = None
    is_active: bool | None = None
    items: list[BOMItemInputDTO] | None = None  # None = no reemplazar items


@dataclass
class BOMItemDTO:
    id: UUID
    bom_id: UUID
    material_id: UUID
    quantity_required: Decimal
    scrap_factor: Decimal
    effective_quantity: Decimal
    sort_order: int
    notes: str | None = None

    @classmethod
    def from_domain(cls, item: BOMItem) -> "BOMItemDTO":
        return cls(
            id=item.id,
            bom_id=item.bom_id,
            material_id=item.material_id,
            quantity_required=item.quantity_required,
            scrap_factor=item.scrap_factor,
            effective_quantity=item.effective_quantity,
            sort_order=item.sort_order,
            notes=item.notes,
        )


@dataclass
class BOMDTO:
    id: UUID
    finished_product_id: UUID
    output_quantity: Decimal
    is_active: bool
    items: list[BOMItemDTO] = field(default_factory=list)
    labor_minutes: int | None = None
    notes: str | None = None

    @classmethod
    def from_domain(cls, bom: BOM, items: list[BOMItem]) -> "BOMDTO":
        return cls(
            id=bom.id,
            finished_product_id=bom.finished_product_id,
            output_quantity=bom.output_quantity,
            is_active=bom.is_active,
            labor_minutes=bom.labor_minutes,
            notes=bom.notes,
            items=[BOMItemDTO.from_domain(i) for i in items],
        )


@dataclass
class BOMWithCostDTO(BOMDTO):
    total_material_cost: Decimal | None = None
    cost_per_unit: Decimal | None = None
    # material_id → nombre del material (enriquecido en use case)
    material_names: dict[UUID, str] = field(default_factory=dict)

    @classmethod
    def from_domain(
        cls,
        bom: BOM,
        items: list[BOMItem],
        total_cost: Decimal | None,
        cost_per_unit: Decimal | None,
        material_names: dict[UUID, str],
    ) -> "BOMWithCostDTO":
        base = BOMDTO.from_domain(bom, items)
        return cls(
            **base.__dict__,
            total_material_cost=total_cost,
            cost_per_unit=cost_per_unit,
            material_names=material_names,
        )


@dataclass
class BOMCostLineDTO:
    material_id: UUID
    material_name: str
    material_sku: str
    unit: str
    quantity_required: Decimal
    scrap_factor: Decimal
    effective_quantity: Decimal
    unit_price: Decimal
    subtotal: Decimal


@dataclass
class BOMCostDetailDTO:
    bom_id: UUID
    finished_product_id: UUID
    output_quantity: Decimal
    lines: list[BOMCostLineDTO]
    total_material_cost: Decimal
    cost_per_unit: Decimal
    labor_minutes: int | None = None
