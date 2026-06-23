from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.models.price_rule import PriceRule


class PriceRuleRepositoryPort(ABC):

    @abstractmethod
    async def get_by_id(self, id: UUID) -> PriceRule | None: ...

    @abstractmethod
    async def list_active(self) -> list[PriceRule]:
        """Retorna todas las reglas activas (sin filtrar por fecha — lo hace PricingService)."""
        ...

    @abstractmethod
    async def list_all(self, skip: int = 0, limit: int = 100) -> list[PriceRule]: ...

    @abstractmethod
    async def create(self, rule: PriceRule) -> PriceRule: ...

    @abstractmethod
    async def update(self, rule: PriceRule) -> PriceRule: ...

    @abstractmethod
    async def delete(self, id: UUID) -> None: ...
