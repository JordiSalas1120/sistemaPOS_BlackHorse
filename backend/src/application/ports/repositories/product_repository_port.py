from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.models.enums import ProductType
from src.domain.models.product import Product


class ProductRepositoryPort(ABC):
    @abstractmethod
    async def get_by_id(self, id: UUID) -> Product | None: ...

    @abstractmethod
    async def get_by_sku(self, sku: str) -> Product | None: ...

    @abstractmethod
    async def list_all(
        self,
        active_only: bool = True,
        category_id: UUID | None = None,
        skip: int = 0,
        limit: int = 50,
        product_type: ProductType | None = None,
    ) -> list[Product]: ...

    @abstractmethod
    async def count(
        self,
        active_only: bool = True,
        category_id: UUID | None = None,
        product_type: ProductType | None = None,
    ) -> int: ...

    @abstractmethod
    async def create(self, product: Product) -> Product: ...

    @abstractmethod
    async def update(self, product: Product) -> Product: ...

    @abstractmethod
    async def delete(self, id: UUID) -> None: ...
