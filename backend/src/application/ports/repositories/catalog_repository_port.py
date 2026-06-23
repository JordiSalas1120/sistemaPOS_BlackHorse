from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.models.catalog import CatalogCategory, CatalogProduct


class CatalogRepositoryPort(ABC):
    """
    Puerto de solo lectura para el catálogo público.
    Solo retorna productos con is_active=True AND show_in_catalog=True.
    Nunca expone wholesale_price ni datos operativos.
    """

    @abstractmethod
    async def list_catalog_products(
        self,
        category_slug: str | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 24,
    ) -> tuple[list[CatalogProduct], int]:
        ...

    @abstractmethod
    async def get_catalog_product_by_sku(self, sku: str) -> CatalogProduct | None:
        ...

    @abstractmethod
    async def list_catalog_categories(self) -> list[CatalogCategory]:
        ...

    @abstractmethod
    async def get_related_products(
        self,
        product_id: UUID,
        category_id: UUID,
        limit: int = 4,
    ) -> list[CatalogProduct]:
        ...
