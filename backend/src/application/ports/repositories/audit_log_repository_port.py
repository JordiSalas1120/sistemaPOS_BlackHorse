from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.models.audit_log import AuditLog


class AuditLogRepositoryPort(ABC):
    @abstractmethod
    async def create(self, log: AuditLog) -> AuditLog: ...

    @abstractmethod
    async def list_by_entity(
        self, entity_type: str, entity_id: UUID, skip: int = 0, limit: int = 50
    ) -> list[AuditLog]: ...

    @abstractmethod
    async def list_recent(self, skip: int = 0, limit: int = 50) -> list[AuditLog]: ...
