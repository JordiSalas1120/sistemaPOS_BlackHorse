from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.models.enums import ProductType
from src.domain.models.product import Product


class WorkshopProductRepositoryPort(ABC):
    """
    Métodos adicionales sobre products para consultas específicas del taller.
    Los adaptadores PostgreSQL implementan esta interfaz extendiendo (o componiendo)
    el ProductRepository existente.
    """

    @abstractmethod
    async def list_raw_materials(
        self,
        skip: int = 0,
        limit: int = 50,
        category_id: UUID | None = None,
        search: str | None = None,
        active_only: bool = True,
    ) -> list[Product]:
        """
        Lista productos con product_type = 'raw_material'.
        search: coincidencia parcial (ILIKE) en name o sku.
        """
        ...

    @abstractmethod
    async def count_raw_materials(
        self,
        category_id: UUID | None = None,
        search: str | None = None,
        active_only: bool = True,
    ) -> int: ...

    @abstractmethod
    async def list_finished_products(
        self,
        skip: int = 0,
        limit: int = 50,
        category_id: UUID | None = None,
        search: str | None = None,
        active_only: bool = True,
    ) -> list[Product]:
        """Lista productos con product_type = 'finished_product'."""
        ...

    @abstractmethod
    async def count_finished_products(
        self,
        category_id: UUID | None = None,
        search: str | None = None,
        active_only: bool = True,
    ) -> int: ...

    @abstractmethod
    async def list_by_type(
        self,
        product_type: ProductType,
        skip: int = 0,
        limit: int = 50,
        active_only: bool = True,
    ) -> list[Product]:
        """Genérico: lista por cualquier product_type."""
        ...

    @abstractmethod
    async def count_by_type(
        self,
        product_type: ProductType,
        active_only: bool = True,
    ) -> int: ...
