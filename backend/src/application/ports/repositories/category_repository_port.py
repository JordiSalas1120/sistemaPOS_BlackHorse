from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.models.product import Category


class CategoryRepositoryPort(ABC):
    @abstractmethod
    async def get_by_id(self, id: UUID) -> Category | None: ...

    @abstractmethod
    async def get_by_slug(self, slug: str) -> Category | None: ...

    @abstractmethod
    async def list_all(self) -> list[Category]: ...

    @abstractmethod
    async def create(self, category: Category) -> Category: ...

    @abstractmethod
    async def update(self, category: Category) -> Category: ...
