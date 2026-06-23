from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.models.inventory import Inventory, InventoryMovement


class InventoryRepositoryPort(ABC):
    @abstractmethod
    async def get_by_product_id(self, product_id: UUID) -> Inventory | None: ...

    @abstractmethod
    async def list_all(self) -> list[Inventory]: ...

    @abstractmethod
    async def list_low_stock(self) -> list[Inventory]: ...

    @abstractmethod
    async def create(self, inventory: Inventory) -> Inventory: ...

    @abstractmethod
    async def update(self, inventory: Inventory) -> Inventory: ...

    @abstractmethod
    async def create_movement(self, movement: InventoryMovement) -> InventoryMovement: ...

    @abstractmethod
    async def list_movements(
        self, product_id: UUID, skip: int = 0, limit: int = 50
    ) -> list[InventoryMovement]: ...
