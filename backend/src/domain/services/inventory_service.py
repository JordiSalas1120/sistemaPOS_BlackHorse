from decimal import Decimal

from src.domain.models.inventory import Inventory


class InventoryService:
    """Reglas de negocio puras para gestión de stock."""

    def can_fulfill_order(
        self, inventory: Inventory, requested_quantity: Decimal
    ) -> bool:
        return inventory.can_fulfill(requested_quantity)

    def get_low_stock_products(
        self, inventories: list[Inventory]
    ) -> list[Inventory]:
        return [inv for inv in inventories if inv.is_low_stock()]

    def compute_new_quantity(
        self, current: Decimal, delta: Decimal
    ) -> Decimal:
        result = current + delta
        if result < Decimal("0"):
            raise ValueError(
                f"El ajuste resultaría en stock negativo: {current} + {delta} = {result}"
            )
        return result
