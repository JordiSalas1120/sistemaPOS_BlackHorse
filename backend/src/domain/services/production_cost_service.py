"""
Servicio de dominio para el cálculo de costos de producción.
No importa nada de infraestructura ni de aplicación.
"""
from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from src.domain.models.production_order import ProductionOrderItem


@dataclass
class CostItemDetail:
    material_id: UUID
    quantity: Decimal
    unit_price: Decimal
    subtotal: Decimal


@dataclass
class ProductionCostBreakdown:
    material_cost: Decimal
    labor_cost: Decimal
    total_cost: Decimal
    cost_per_unit: Decimal
    quantity_to_produce: Decimal
    items_detail: list[CostItemDetail] = field(default_factory=list)


class ProductionCostService:
    """
    Calcula el costo de producción a partir de los ítems del BOM y,
    opcionalmente, el costo de mano de obra.
    """

    def calculate_production_cost(
        self,
        bom_items: list[ProductionOrderItem],
        material_prices: dict[UUID, Decimal],
        quantity_to_produce: Decimal,
        labor_minutes: int | None = None,
        hourly_rate: Decimal | None = None,
    ) -> ProductionCostBreakdown:
        """
        Calcula el costo de producción completo.

        Args:
            bom_items: Ítems del BOM (o de la orden, con sus snapshots)
            material_prices: Mapa material_id → precio unitario actual
            quantity_to_produce: Unidades a fabricar
            labor_minutes: Minutos de mano de obra por lote (opcional)
            hourly_rate: Tarifa horaria en ARS (opcional)

        Returns:
            ProductionCostBreakdown con el desglose completo.
        """
        items_detail: list[CostItemDetail] = []
        material_cost = Decimal("0")

        for item in bom_items:
            unit_price = material_prices.get(item.material_id, item.unit_cost_snapshot)
            total_qty = item.quantity_required * quantity_to_produce
            subtotal = total_qty * unit_price
            material_cost += subtotal
            items_detail.append(
                CostItemDetail(
                    material_id=item.material_id,
                    quantity=total_qty,
                    unit_price=unit_price,
                    subtotal=subtotal,
                )
            )

        labor_cost = Decimal("0")
        if labor_minutes is not None and hourly_rate is not None and labor_minutes > 0:
            labor_cost = (Decimal(str(labor_minutes)) / Decimal("60")) * hourly_rate

        total_cost = material_cost + labor_cost
        cost_per_unit = (
            total_cost / quantity_to_produce if quantity_to_produce else Decimal("0")
        )

        return ProductionCostBreakdown(
            material_cost=material_cost,
            labor_cost=labor_cost,
            total_cost=total_cost,
            cost_per_unit=cost_per_unit,
            quantity_to_produce=quantity_to_produce,
            items_detail=items_detail,
        )
