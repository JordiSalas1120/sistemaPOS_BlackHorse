from datetime import datetime
from uuid import UUID

from src.application.dtos.production_dto import ProductionOrderListDTO, _to_dto
from src.application.ports.repositories.production_order_repository_port import (
    ProductionOrderRepositoryPort,
)
from src.domain.models.enums import ProductionOrderStatus


class ListProductionOrdersUseCase:
    def __init__(self, order_repo: ProductionOrderRepositoryPort):
        self._order_repo = order_repo

    async def execute(
        self,
        status: ProductionOrderStatus | None = None,
        finished_product_id: UUID | None = None,
        produced_by: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> ProductionOrderListDTO:
        orders, total = await self._order_repo.list_orders(
            status=status,
            finished_product_id=finished_product_id,
            produced_by=produced_by,
            date_from=date_from,
            date_to=date_to,
            skip=skip,
            limit=limit,
        )
        return ProductionOrderListDTO(
            items=[_to_dto(o, []) for o in orders],
            total=total,
            skip=skip,
            limit=limit,
        )
