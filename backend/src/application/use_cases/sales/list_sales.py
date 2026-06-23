from datetime import datetime
from uuid import UUID

from src.application.dtos.sale_dto import SaleDTO, SaleListDTO
from src.application.ports.repositories.product_repository_port import ProductRepositoryPort
from src.application.ports.repositories.sale_repository_port import SaleRepositoryPort
from src.application.use_cases.sales.get_sale import _item_to_dto, _to_dto


class ListSalesUseCase:
    def __init__(self, sale_repo: SaleRepositoryPort, product_repo: ProductRepositoryPort):
        self._sale_repo = sale_repo
        self._product_repo = product_repo

    async def execute(
        self,
        client_id: UUID | None = None,
        status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> SaleListDTO:
        sales = await self._sale_repo.list_all(
            client_id=client_id, status=status, date_from=date_from, date_to=date_to,
            skip=skip, limit=limit
        )
        total = await self._sale_repo.count(
            client_id=client_id, status=status, date_from=date_from, date_to=date_to
        )

        # Batch: cargar todos los productos referenciados en una sola query
        product_ids = {item.product_id for sale in sales for item in sale.items}
        products = {}
        for pid in product_ids:
            p = await self._product_repo.get_by_id(pid)
            if p:
                products[pid] = p

        result: list[SaleDTO] = []
        for sale in sales:
            items_enriched = [
                _item_to_dto(
                    item,
                    product_sku=products[item.product_id].sku if item.product_id in products else "—",
                    product_name=products[item.product_id].name if item.product_id in products else "—",
                )
                for item in sale.items
            ]
            result.append(_to_dto(sale, items_enriched))

        return SaleListDTO(items=result, total=total, skip=skip, limit=limit)
