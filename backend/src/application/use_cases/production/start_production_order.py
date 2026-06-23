from datetime import datetime, timezone
from uuid import UUID

from src.application.dtos.production_dto import ProductionOrderDTO, _to_dto
from src.application.exceptions import BusinessRuleViolation, InsufficientStockError, NotFoundError
from src.application.ports.repositories.inventory_repository_port import InventoryRepositoryPort
from src.application.ports.repositories.production_order_repository_port import (
    ProductionOrderRepositoryPort,
)
from src.domain.models.enums import ProductionOrderStatus


class StartProductionOrderUseCase:
    """
    Cambia el estado DRAFT → IN_PROGRESS después de validar que hay stock suficiente
    para todos los materiales requeridos.
    """

    def __init__(
        self,
        order_repo: ProductionOrderRepositoryPort,
        inventory_repo: InventoryRepositoryPort,
    ):
        self._order_repo = order_repo
        self._inventory_repo = inventory_repo

    async def execute(self, order_id: UUID) -> ProductionOrderDTO:
        # 1. Cargar orden con ítems
        result = await self._order_repo.get_order_with_items(order_id)
        if not result:
            raise NotFoundError("Orden de producción", str(order_id))

        order, items = result

        if not order.can_start():
            raise BusinessRuleViolation(
                f"No se puede iniciar una orden en estado '{order.status}'. "
                "Solo las órdenes en estado DRAFT pueden iniciarse."
            )

        # 2. Validar stock de cada material
        shortfalls: list[dict] = []

        for item in items:
            required_total = item.quantity_required * order.quantity_to_produce
            inventory = await self._inventory_repo.get_by_product_id(item.material_id)

            if not inventory:
                shortfalls.append({
                    "material_id": str(item.material_id),
                    "required": float(required_total),
                    "available": 0.0,
                })
                continue

            if inventory.quantity_on_hand < required_total:
                shortfalls.append({
                    "material_id": str(item.material_id),
                    "required": float(required_total),
                    "available": float(inventory.quantity_on_hand),
                })

        if shortfalls:
            first = shortfalls[0]
            raise InsufficientStockError(
                product_id=first["material_id"],
                available=first["available"],
                requested=first["required"],
            )

        # 3. Cambiar estado
        now = datetime.now(timezone.utc)
        order.status = ProductionOrderStatus.IN_PROGRESS
        order.started_at = now
        order.updated_at = now

        updated = await self._order_repo.update_order(order)
        items = await self._order_repo.get_order_items(order_id)
        return _to_dto(updated, items)
