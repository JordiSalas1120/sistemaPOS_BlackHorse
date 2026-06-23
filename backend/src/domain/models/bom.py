from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass
class BOMItem:
    """Línea de una receta de producción."""
    id: UUID
    bom_id: UUID
    material_id: UUID
    quantity_required: Decimal        # cantidad neta requerida
    sort_order: int = 0
    scrap_factor: Decimal = Decimal("0")  # 0.05 = 5% de desperdicio
    notes: str | None = None

    @property
    def effective_quantity(self) -> Decimal:
        """Cantidad real a consumir incluyendo desperdicio: qty × (1 + scrap)."""
        return self.quantity_required * (Decimal("1") + self.scrap_factor)


@dataclass
class BOM:
    """
    Bill of Materials — receta de producción para un producto terminado.
    Una BOM pertenece a exactamente un producto de tipo finished_product.
    """
    id: UUID
    finished_product_id: UUID
    output_quantity: Decimal          # cuántas unidades produce esta receta
    is_active: bool
    created_at: datetime
    updated_at: datetime
    labor_minutes: int | None = None  # mano de obra estimada en minutos por lote
    notes: str | None = None
    items: list[BOMItem] = field(default_factory=list)

    def calculate_material_cost(self, prices: dict[UUID, Decimal]) -> Decimal:
        """
        Calcula el costo total de materiales para producir `output_quantity` unidades.

        Args:
            prices: Mapa { material_id → costo_unitario } con los precios actuales
                    de cada materia prima (normalmente cost_price del producto o base_price).

        Returns:
            Costo total de materiales para el lote completo (output_quantity unidades).
            Para obtener el costo por unidad: resultado / output_quantity.

        Raises:
            KeyError: Si algún material_id no está presente en el dict `prices`.
                      El caller debe asegurar que todos los materiales estén incluidos.
        """
        total = Decimal("0")
        for item in self.items:
            unit_price = prices[item.material_id]
            total += item.effective_quantity * unit_price
        return total

    def cost_per_unit(self, prices: dict[UUID, Decimal]) -> Decimal:
        """Costo de materiales por unidad de producto terminado."""
        if self.output_quantity == Decimal("0"):
            return Decimal("0")
        return self.calculate_material_cost(prices) / self.output_quantity
