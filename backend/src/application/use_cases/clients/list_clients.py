from src.application.dtos.client_dto import ClientListDTO
from src.application.ports.repositories.client_repository_port import ClientRepositoryPort
from src.application.use_cases.clients.get_client import _to_dto


class ListClientsUseCase:
    def __init__(self, client_repo: ClientRepositoryPort):
        self._client_repo = client_repo

    async def execute(
        self,
        active_only: bool = True,
        client_type: str | None = None,
        tag: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> ClientListDTO:
        clients = await self._client_repo.list_all(
            active_only=active_only, client_type=client_type, tag=tag, skip=skip, limit=limit
        )
        total = await self._client_repo.count(
            active_only=active_only, client_type=client_type, tag=tag
        )
        return ClientListDTO(items=[_to_dto(c) for c in clients], total=total, skip=skip, limit=limit)
