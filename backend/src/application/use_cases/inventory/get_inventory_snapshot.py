from uuid import UUID

from src.application.dtos.inventory_dto import InventoryDTO, MovementDTO
from src.application.exceptions import NotFoundError
from src.application.ports.repositories.inventory_repository_port import InventoryRepositoryPort
from src.application.ports.repositories.product_repository_port import ProductRepositoryPort


class GetInventorySnapshotUseCase:
    """Lista el stock de todos los productos activos con su información."""

    def __init__(
        self,
        inventory_repo: InventoryRepositoryPort,
        product_repo: ProductRepositoryPort,
    ):
        self._inventory_repo = inventory_repo
        self._product_repo = product_repo

    async def execute(self) -> list[InventoryDTO]:
        inventories = await self._inventory_repo.list_all()
        product_ids = {inv.product_id for inv in inventories}

        # Batch: traer solo los productos que tienen inventario
        products = {
            p.id: p
            for p in await self._product_repo.list_all(active_only=True, limit=10000)
            if p.id in product_ids
        }

        return [
            InventoryDTO(
                product_id=inv.product_id,
                product_sku=products[inv.product_id].sku if inv.product_id in products else "—",
                product_name=products[inv.product_id].name if inv.product_id in products else "—",
                quantity_on_hand=inv.quantity_on_hand,
                low_stock_threshold=inv.low_stock_threshold,
                is_low_stock=inv.is_low_stock(),
            )
            for inv in inventories
            if inv.product_id in products
        ]


class GetProductMovementsUseCase:
    """Historial de movimientos de stock de un producto."""

    def __init__(
        self,
        inventory_repo: InventoryRepositoryPort,
        product_repo: ProductRepositoryPort,
    ):
        self._inventory_repo = inventory_repo
        self._product_repo = product_repo

    async def execute(self, product_id: UUID, skip: int = 0, limit: int = 50) -> list[MovementDTO]:
        product = await self._product_repo.get_by_id(product_id)
        if not product:
            raise NotFoundError("Producto", str(product_id))

        movements = await self._inventory_repo.list_movements(product_id, skip=skip, limit=limit)
        return [
            MovementDTO(
                id=m.id,
                product_id=m.product_id,
                movement_type=m.movement_type,
                quantity_delta=m.quantity_delta,
                quantity_before=m.quantity_before,
                quantity_after=m.quantity_after,
                created_by=m.created_by,
                notes=m.notes,
            )
            for m in movements
        ]
