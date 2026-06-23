from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.models.client import Client


class ClientRepositoryPort(ABC):

    @abstractmethod
    async def get_by_id(self, id: UUID) -> Client | None: ...

    @abstractmethod
    async def get_by_phone(self, phone: str) -> Client | None: ...

    @abstractmethod
    async def get_by_email(self, email: str) -> Client | None: ...

    @abstractmethod
    async def list_all(
        self,
        active_only: bool = True,
        client_type: str | None = None,
        tag: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Client]: ...

    @abstractmethod
    async def count(
        self,
        active_only: bool = True,
        client_type: str | None = None,
        tag: str | None = None,
    ) -> int: ...

    @abstractmethod
    async def create(self, client: Client) -> Client: ...

    @abstractmethod
    async def update(self, client: Client) -> Client: ...
