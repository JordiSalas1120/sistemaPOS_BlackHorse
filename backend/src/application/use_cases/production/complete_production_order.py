import uuid
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from src.application.dtos.production_dto import (
    CompleteProductionOrderDTO,
    ProductionOrderDTO,
    _to_dto,
)
from src.application.exceptions import BusinessRuleViolation, InsufficientStockError, NotFoundError
from src.application.ports.repositories.inventory_repository_port import InventoryRepositoryPort
from src.application.ports.repositories.production_order_repository_port import (
    ProductionOrderRepositoryPort,
)
from src.domain.models.enums import MovementType, ProductionOrderStatus
from src.domain.models.inventory import InventoryMovement
from src.domain.services.production_cost_service import ProductionCostService


class CompleteProductionOrderUseCase:
    """
    Transacción atómica:
    1. Descuenta inventario de cada material (PRODUCTION_CONSUMPTION)
    2. Acredita el producto terminado (PRODUCTION_OUTPUT)
    3. Calcula y guarda unit_cost_snapshot
    4. Cambia status a COMPLETED

    Toda la operación comparte la misma AsyncSession (garantizada por FastAPI Depends caching),
    por lo que un error en cualquier paso revierte todo automáticamente.
    """

    def __init__(
        self,
        order_repo: ProductionOrderRepositoryPort,
        inventory_repo: InventoryRepositoryPort,
        cost_service: ProductionCostService,
    ):
        self._order_repo = order_repo
        self._inventory_repo = inventory_repo
        self._cost_service = cost_service

    async def execute(
        self, order_id: UUID, dto: CompleteProductionOrderDTO, actor: str = "system"
    ) -> ProductionOrderDTO:
        # 1. Cargar orden
        result = await self._order_repo.get_order_with_items(order_id)
        if not result:
            raise NotFoundError("Orden de producción", str(order_id))

        order, items = result

        if not order.can_complete():
            raise BusinessRuleViolation(
                f"No se puede completar una orden en estado '{order.status}'. "
                "Solo las órdenes IN_PROGRESS pueden completarse."
            )

        quantity_produced = dto.quantity_produced
        if quantity_produced <= Decimal("0"):
            raise BusinessRuleViolation("La cantidad producida debe ser mayor a 0.")
        if quantity_produced > order.quantity_to_produce:
            raise BusinessRuleViolation(
                f"La cantidad producida ({quantity_produced}) no puede superar "
                f"la planificada ({order.quantity_to_produce})."
            )

        now = datetime.now(timezone.utc)

        # 2. Descontar inventario de materiales (PRODUCTION_CONSUMPTION)
        for item in items:
            consumed = item.quantity_required * quantity_produced
            inventory = await self._inventory_repo.get_by_product_id(item.material_id)

            if not inventory:
                raise NotFoundError("Inventario de material", str(item.material_id))

            if inventory.quantity_on_hand < consumed:
                raise InsufficientStockError(
                    product_id=str(item.material_id),
                    available=float(inventory.quantity_on_hand),
                    requested=float(consumed),
                )

            qty_before = inventory.quantity_on_hand
            inventory.quantity_on_hand -= consumed
            await self._inventory_repo.update(inventory)

            movement = InventoryMovement(
                id=uuid.uuid4(),
                product_id=item.material_id,
                movement_type=MovementType.PRODUCTION_CONSUMPTION,
                quantity_delta=-consumed,
                quantity_before=qty_before,
                quantity_after=inventory.quantity_on_hand,
                created_by=actor,
                created_at=now,
                reference_id=order_id,
                notes=f"Consumo en orden {order.order_number}",
            )
            await self._inventory_repo.create_movement(movement)

            item.quantity_consumed = consumed

        # 3. Acreditar producto terminado (PRODUCTION_OUTPUT)
        finished_inventory = await self._inventory_repo.get_by_product_id(
            order.finished_product_id
        )
        if not finished_inventory:
            raise NotFoundError(
                "Inventario del producto terminado", str(order.finished_product_id)
            )

        qty_before_finished = finished_inventory.quantity_on_hand
        finished_inventory.quantity_on_hand += quantity_produced
        finished_inventory.last_restocked_at = now
        await self._inventory_repo.update(finished_inventory)

        output_movement = InventoryMovement(
            id=uuid.uuid4(),
            product_id=order.finished_product_id,
            movement_type=MovementType.PRODUCTION_OUTPUT,
            quantity_delta=quantity_produced,
            quantity_before=qty_before_finished,
            quantity_after=finished_inventory.quantity_on_hand,
            created_by=actor,
            created_at=now,
            reference_id=order_id,
            notes=f"Producción completada: {order.order_number}",
        )
        await self._inventory_repo.create_movement(output_movement)

        # 4. Calcular costo unitario real y actualizar ítems
        material_prices = {item.material_id: item.unit_cost_snapshot for item in items}
        cost_breakdown = self._cost_service.calculate_production_cost(
            bom_items=items,
            material_prices=material_prices,
            quantity_to_produce=quantity_produced,
        )

        await self._order_repo.update_order_items(items)

        # 5. Actualizar orden
        order.status = ProductionOrderStatus.COMPLETED
        order.quantity_produced = quantity_produced
        order.completed_at = now
        order.updated_at = now
        order.unit_cost_snapshot = cost_breakdown.cost_per_unit
        if dto.notes:
            order.notes = dto.notes

        updated = await self._order_repo.update_order(order)
        return _to_dto(updated, items)
