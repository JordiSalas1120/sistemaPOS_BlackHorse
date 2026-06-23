from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from src.domain.models.enums import ProductionOrderStatus


@dataclass
class ProductionOrderItem:
    id: UUID
    order_id: UUID
    material_id: UUID
    quantity_required: Decimal   # snapshot del BOM al crear la orden (por unidad de salida)
    unit_cost_snapshot: Decimal  # precio del insumo al momento de la orden
    quantity_consumed: Decimal = Decimal("0")   # real al completar
    notes: str | None = None

    @property
    def subtotal_cost(self) -> Decimal:
        """Costo de este ítem usando la cantidad consumida real (o requerida si aún no completó)."""
        qty = self.quantity_consumed if self.quantity_consumed > Decimal("0") else self.quantity_required
        return qty * self.unit_cost_snapshot


@dataclass
class ProductionOrder:
    id: UUID
    order_number: str
    bom_id: UUID
    finished_product_id: UUID
    quantity_to_produce: Decimal
    produced_by: str
    status: ProductionOrderStatus
    created_at: datetime
    updated_at: datetime
    quantity_produced: Decimal = Decimal("0")
    unit_cost_snapshot: Decimal | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None
    notes: str | None = None
    items: list[ProductionOrderItem] = field(default_factory=list)

    # ── Transiciones de estado ────────────────────────────────────────────

    def can_start(self) -> bool:
        """Solo se puede iniciar desde DRAFT."""
        return self.status == ProductionOrderStatus.DRAFT

    def can_complete(self) -> bool:
        """Solo se puede completar desde IN_PROGRESS."""
        return self.status == ProductionOrderStatus.IN_PROGRESS

    def can_cancel(self) -> bool:
        """Se puede cancelar desde DRAFT o IN_PROGRESS. Una orden COMPLETED no se cancela."""
        return self.status in (
            ProductionOrderStatus.DRAFT,
            ProductionOrderStatus.IN_PROGRESS,
        )

    # ── Cálculos de costo ─────────────────────────────────────────────────
    # quantity_required de cada ítem es POR UNIDAD de producto terminado.
    # Por eso el costo por unidad es Σ(quantity_required × unit_cost_snapshot)
    # y el costo total del lote escala por quantity_to_produce.

    def calculate_cost_per_unit(self) -> Decimal:
        """Costo de materiales por unidad de producto terminado."""
        return sum(
            (item.quantity_required * item.unit_cost_snapshot for item in self.items),
            Decimal("0"),
        )

    def calculate_total_material_cost(self) -> Decimal:
        """Costo de materiales para todo el lote (por unidad × cantidad planificada)."""
        return self.calculate_cost_per_unit() * self.quantity_to_produce

    def is_partial_completion(self) -> bool:
        """True si la cantidad producida es menor a la planificada."""
        return self.quantity_produced < self.quantity_to_produce
