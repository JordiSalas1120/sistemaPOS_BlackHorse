from uuid import UUID

from src.application.dtos.client_dto import ClientDTO
from src.application.exceptions import NotFoundError
from src.application.ports.repositories.client_repository_port import ClientRepositoryPort
from src.domain.models.client import Client


def _to_dto(c: Client) -> ClientDTO:
    return ClientDTO(
        id=c.id,
        full_name=c.full_name,
        phone=c.phone,
        email=c.email,
        address=c.address,
        client_type=c.client_type,
        tags=c.tags,
        notes=c.notes,
        whatsapp_opt_in=c.whatsapp_opt_in,
        is_active=c.is_active,
        created_at=c.created_at,
        updated_at=c.updated_at,
        last_purchase_at=c.last_purchase_at,
    )


class GetClientUseCase:
    def __init__(self, client_repo: ClientRepositoryPort):
        self._client_repo = client_repo

    async def execute(self, client_id: UUID) -> ClientDTO:
        client = await self._client_repo.get_by_id(client_id)
        if not client:
            raise NotFoundError("Cliente", str(client_id))
        return _to_dto(client)
