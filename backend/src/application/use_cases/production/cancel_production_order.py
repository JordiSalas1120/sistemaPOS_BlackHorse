from datetime import datetime, timezone
from uuid import UUID

from src.application.dtos.production_dto import ProductionOrderDTO, _to_dto
from src.application.exceptions import BusinessRuleViolation, NotFoundError
from src.application.ports.repositories.production_order_repository_port import (
    ProductionOrderRepositoryPort,
)
from src.domain.models.enums import ProductionOrderStatus


class CancelProductionOrderUseCase:
    """
    Cancela una orden en DRAFT o IN_PROGRESS.
    Si estaba IN_PROGRESS, NO revierte stock — el operario debe hacer un ajuste manual
    de inventario si ya había consumido materiales parcialmente.
    """

    def __init__(self, order_repo: ProductionOrderRepositoryPort):
        self._order_repo = order_repo

    async def execute(self, order_id: UUID, reason: str) -> ProductionOrderDTO:
        result = await self._order_repo.get_order_with_items(order_id)
        if not result:
            raise NotFoundError("Orden de producción", str(order_id))

        order, items = result

        if not order.can_cancel():
            raise BusinessRuleViolation(
                f"No se puede cancelar una orden en estado '{order.status}'. "
                "Solo DRAFT e IN_PROGRESS pueden cancelarse."
            )

        now = datetime.now(timezone.utc)
        was_in_progress = order.status == ProductionOrderStatus.IN_PROGRESS

        order.status = ProductionOrderStatus.CANCELLED
        order.cancelled_at = now
        order.updated_at = now
        cancellation_note = f"[CANCELADO {now.isoformat()}] {reason}"
        if was_in_progress:
            cancellation_note += " — Estaba EN PROGRESO. Verificar stock manualmente."
        order.notes = (
            f"{order.notes}\n{cancellation_note}" if order.notes else cancellation_note
        )

        updated = await self._order_repo.update_order(order)
        return _to_dto(updated, items)
