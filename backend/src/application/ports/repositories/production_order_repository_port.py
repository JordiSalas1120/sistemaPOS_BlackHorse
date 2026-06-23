from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from src.domain.models.enums import ProductionOrderStatus
from src.domain.models.production_order import ProductionOrder, ProductionOrderItem


class ProductionOrderRepositoryPort(ABC):

    @abstractmethod
    async def create_order(
        self,
        order: ProductionOrder,
        items: list[ProductionOrderItem],
    ) -> ProductionOrder:
        """Persiste la orden y sus ítems en una sola operación. Retorna la orden con ítems."""
        ...

    @abstractmethod
    async def get_order(self, order_id: UUID) -> ProductionOrder | None:
        """Retorna la orden sin ítems (cabecera). None si no existe."""
        ...

    @abstractmethod
    async def get_order_with_items(
        self, order_id: UUID
    ) -> tuple[ProductionOrder, list[ProductionOrderItem]] | None:
        """Retorna la orden con sus ítems cargados. None si no existe."""
        ...

    @abstractmethod
    async def list_orders(
        self,
        status: ProductionOrderStatus | None = None,
        finished_product_id: UUID | None = None,
        produced_by: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[ProductionOrder], int]:
        """Retorna (lista de órdenes, total sin paginación)."""
        ...

    @abstractmethod
    async def update_order(self, order: ProductionOrder) -> ProductionOrder:
        """Persiste cambios en la cabecera de la orden (status, timestamps, snapshots)."""
        ...

    @abstractmethod
    async def update_order_items(
        self, items: list[ProductionOrderItem]
    ) -> list[ProductionOrderItem]:
        """Actualiza quantity_consumed en los ítems al completar la orden."""
        ...

    @abstractmethod
    async def next_order_number(self, year: int) -> str:
        """
        Genera el próximo número de orden con formato ORD-YYYY-NNNNN.
        Usa COUNT(*) por año igual que SaleRepository.next_sale_number().
        """
        ...

    @abstractmethod
    async def get_order_items(self, order_id: UUID) -> list[ProductionOrderItem]:
        """Retorna los ítems de una orden. Lista vacía si la orden no existe."""
        ...
