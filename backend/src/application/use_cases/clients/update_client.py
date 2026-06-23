import uuid
from datetime import datetime, timezone
from uuid import UUID

from src.application.dtos.client_dto import ClientDTO, UpdateClientDTO
from src.application.exceptions import AlreadyExistsError, NotFoundError
from src.application.ports.repositories.audit_log_repository_port import AuditLogRepositoryPort
from src.application.ports.repositories.client_repository_port import ClientRepositoryPort
from src.application.use_cases.clients.get_client import _to_dto
from src.domain.models.audit_log import AuditLog
from src.domain.models.enums import AuditAction


class UpdateClientUseCase:
    def __init__(self, client_repo: ClientRepositoryPort, audit_repo: AuditLogRepositoryPort):
        self._client_repo = client_repo
        self._audit_repo = audit_repo

    async def execute(self, client_id: UUID, dto: UpdateClientDTO, actor: str = "system") -> ClientDTO:
        client = await self._client_repo.get_by_id(client_id)
        if not client:
            raise NotFoundError("Cliente", str(client_id))

        before = {"full_name": client.full_name, "phone": client.phone, "client_type": client.client_type}

        if dto.phone and dto.phone != client.phone:
            existing = await self._client_repo.get_by_phone(dto.phone)
            if existing and existing.id != client_id:
                raise AlreadyExistsError("Cliente", "teléfono", dto.phone)
            client.phone = dto.phone

        if dto.email and dto.email != client.email:
            existing = await self._client_repo.get_by_email(dto.email)
            if existing and existing.id != client_id:
                raise AlreadyExistsError("Cliente", "email", dto.email)
            client.email = dto.email

        if dto.full_name is not None:
            client.full_name = dto.full_name
        if dto.address is not None:
            client.address = dto.address
        if dto.notes is not None:
            client.notes = dto.notes
        if dto.client_type is not None:
            client.client_type = dto.client_type
        if dto.whatsapp_opt_in is not None:
            client.whatsapp_opt_in = dto.whatsapp_opt_in
        if dto.is_active is not None:
            client.is_active = dto.is_active

        client.updated_at = datetime.now(timezone.utc)
        saved = await self._client_repo.update(client)

        await self._audit_repo.create(AuditLog(
            id=uuid.uuid4(),
            entity_type="client",
            entity_id=client_id,
            action=AuditAction.UPDATE,
            actor=actor,
            payload={"before": before, "after": {"full_name": saved.full_name, "phone": saved.phone}},
            created_at=datetime.now(timezone.utc),
        ))

        return _to_dto(saved)
