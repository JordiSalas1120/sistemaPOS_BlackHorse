from src.application.dtos.inventory_dto import InventoryDTO
from src.application.ports.repositories.inventory_repository_port import InventoryRepositoryPort
from src.application.ports.repositories.product_repository_port import ProductRepositoryPort


class GetLowStockAlertsUseCase:
    def __init__(
        self,
        inventory_repo: InventoryRepositoryPort,
        product_repo: ProductRepositoryPort,
    ):
        self._inventory_repo = inventory_repo
        self._product_repo = product_repo

    async def execute(self) -> list[InventoryDTO]:
        low_stock = await self._inventory_repo.list_low_stock()

        result: list[InventoryDTO] = []
        for inv in low_stock:
            product = await self._product_repo.get_by_id(inv.product_id)
            if product and product.is_active:
                result.append(InventoryDTO(
                    product_id=inv.product_id,
                    product_sku=product.sku,
                    product_name=product.name,
                    quantity_on_hand=inv.quantity_on_hand,
                    low_stock_threshold=inv.low_stock_threshold,
                    is_low_stock=inv.is_low_stock(),
                ))
        return result
