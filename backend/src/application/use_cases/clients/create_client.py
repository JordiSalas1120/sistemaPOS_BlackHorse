import uuid
from datetime import datetime, timezone

from src.application.dtos.client_dto import ClientDTO, CreateClientDTO
from src.application.exceptions import AlreadyExistsError
from src.application.ports.repositories.audit_log_repository_port import AuditLogRepositoryPort
from src.application.ports.repositories.client_repository_port import ClientRepositoryPort
from src.application.use_cases.clients.get_client import _to_dto
from src.domain.models.audit_log import AuditLog
from src.domain.models.client import Client
from src.domain.models.enums import AuditAction


class CreateClientUseCase:
    def __init__(self, client_repo: ClientRepositoryPort, audit_repo: AuditLogRepositoryPort):
        self._client_repo = client_repo
        self._audit_repo = audit_repo

    async def execute(self, dto: CreateClientDTO, actor: str = "system") -> ClientDTO:
        if await self._client_repo.get_by_phone(dto.phone):
            raise AlreadyExistsError("Cliente", "teléfono", dto.phone)

        if dto.email and await self._client_repo.get_by_email(dto.email):
            raise AlreadyExistsError("Cliente", "email", dto.email)

        now = datetime.now(timezone.utc)
        client = Client(
            id=uuid.uuid4(),
            full_name=dto.full_name,
            phone=dto.phone,
            email=dto.email,
            address=dto.address,
            client_type=dto.client_type,
            tags=list(dto.tags),
            notes=dto.notes,
            whatsapp_opt_in=dto.whatsapp_opt_in,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        saved = await self._client_repo.create(client)

        await self._audit_repo.create(AuditLog(
            id=uuid.uuid4(),
            entity_type="client",
            entity_id=saved.id,
            action=AuditAction.CREATE,
            actor=actor,
            payload={"after": {"full_name": dto.full_name, "phone": dto.phone, "client_type": dto.client_type}},
            created_at=now,
        ))

        return _to_dto(saved)
