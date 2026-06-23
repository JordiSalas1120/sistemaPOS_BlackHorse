from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from src.domain.models.sale import Sale


class SaleRepositoryPort(ABC):

    @abstractmethod
    async def get_by_id(self, id: UUID) -> Sale | None: ...

    @abstractmethod
    async def get_by_sale_number(self, sale_number: str) -> Sale | None: ...

    @abstractmethod
    async def list_all(
        self,
        client_id: UUID | None = None,
        status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Sale]: ...

    @abstractmethod
    async def count(
        self,
        client_id: UUID | None = None,
        status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> int: ...

    @abstractmethod
    async def next_sale_number(self, year: int) -> str:
        """Genera el próximo número de venta con formato VTA-YYYY-NNNNN."""
        ...

    @abstractmethod
    async def create(self, sale: Sale) -> Sale: ...

    @abstractmethod
    async def update(self, sale: Sale) -> Sale: ...
