import uuid
from datetime import datetime, timezone
from uuid import UUID

from src.application.dtos.client_dto import ClientDTO
from src.application.exceptions import NotFoundError
from src.application.ports.repositories.audit_log_repository_port import AuditLogRepositoryPort
from src.application.ports.repositories.client_repository_port import ClientRepositoryPort
from src.application.use_cases.clients.get_client import _to_dto
from src.domain.models.audit_log import AuditLog
from src.domain.models.enums import AuditAction


class AddTagUseCase:
    def __init__(self, client_repo: ClientRepositoryPort, audit_repo: AuditLogRepositoryPort):
        self._client_repo = client_repo
        self._audit_repo = audit_repo

    async def execute(self, client_id: UUID, tag: str, actor: str = "system") -> ClientDTO:
        client = await self._client_repo.get_by_id(client_id)
        if not client:
            raise NotFoundError("Cliente", str(client_id))

        client.add_tag(tag)
        client.updated_at = datetime.now(timezone.utc)
        saved = await self._client_repo.update(client)

        await self._audit_repo.create(AuditLog(
            id=uuid.uuid4(),
            entity_type="client",
            entity_id=client_id,
            action=AuditAction.UPDATE,
            actor=actor,
            payload={"tag_added": tag, "tags_after": saved.tags},
            created_at=datetime.now(timezone.utc),
        ))

        return _to_dto(saved)


class RemoveTagUseCase:
    def __init__(self, client_repo: ClientRepositoryPort, audit_repo: AuditLogRepositoryPort):
        self._client_repo = client_repo
        self._audit_repo = audit_repo

    async def execute(self, client_id: UUID, tag: str, actor: str = "system") -> ClientDTO:
        client = await self._client_repo.get_by_id(client_id)
        if not client:
            raise NotFoundError("Cliente", str(client_id))

        client.remove_tag(tag)
        client.updated_at = datetime.now(timezone.utc)
        saved = await self._client_repo.update(client)

        await self._audit_repo.create(AuditLog(
            id=uuid.uuid4(),
            entity_type="client",
            entity_id=client_id,
            action=AuditAction.UPDATE,
            actor=actor,
            payload={"tag_removed": tag, "tags_after": saved.tags},
            created_at=datetime.now(timezone.utc),
        ))

        return _to_dto(saved)
