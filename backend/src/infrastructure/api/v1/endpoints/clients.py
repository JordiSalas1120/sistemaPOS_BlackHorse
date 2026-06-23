from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from src.application.dtos.client_dto import CreateClientDTO, UpdateClientDTO
from src.application.exceptions import AlreadyExistsError, NotFoundError
from src.application.ports.repositories.audit_log_repository_port import AuditLogRepositoryPort
from src.application.ports.repositories.client_repository_port import ClientRepositoryPort
from src.application.use_cases.clients.create_client import CreateClientUseCase
from src.application.use_cases.clients.get_client import GetClientUseCase
from src.application.use_cases.clients.list_clients import ListClientsUseCase
from src.application.use_cases.clients.manage_tags import AddTagUseCase, RemoveTagUseCase
from src.application.use_cases.clients.update_client import UpdateClientUseCase
from src.dependencies import get_audit_repo, get_client_repo
from src.domain.models.enums import ClientType
from src.infrastructure.api.v1.schemas.client_schema import (
    ClientCreateRequest,
    ClientListResponse,
    ClientResponse,
    ClientUpdateRequest,
    TagRequest,
)
from src.infrastructure.api.v1.schemas.common_schema import MessageResponse

router = APIRouter(prefix="/clients", tags=["Clientes"])


def _actor(x_actor: str = Header(default="api")) -> str:
    return x_actor


def _client_to_response(dto) -> ClientResponse:
    return ClientResponse(**dto.__dict__)


@router.get("", response_model=ClientListResponse)
async def list_clients(
    active_only: bool = Query(True),
    client_type: ClientType | None = Query(None),
    tag: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    client_repo: ClientRepositoryPort = Depends(get_client_repo),
):
    uc = ListClientsUseCase(client_repo)
    result = await uc.execute(
        active_only=active_only,
        client_type=client_type,
        tag=tag,
        skip=skip,
        limit=limit,
    )
    return ClientListResponse(
        items=[_client_to_response(c) for c in result.items],
        total=result.total,
        skip=result.skip,
        limit=result.limit,
    )


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    body: ClientCreateRequest,
    actor: str = Depends(_actor),
    client_repo: ClientRepositoryPort = Depends(get_client_repo),
    audit_repo: AuditLogRepositoryPort = Depends(get_audit_repo),
):
    uc = CreateClientUseCase(client_repo, audit_repo)
    dto = CreateClientDTO(
        full_name=body.full_name,
        phone=body.phone,
        client_type=body.client_type,
        email=body.email,
        address=body.address,
        notes=body.notes,
        whatsapp_opt_in=body.whatsapp_opt_in,
        tags=body.tags,
    )
    try:
        result = await uc.execute(dto, actor=actor)
    except AlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return _client_to_response(result)


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: UUID,
    client_repo: ClientRepositoryPort = Depends(get_client_repo),
):
    uc = GetClientUseCase(client_repo)
    try:
        result = await uc.execute(client_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return _client_to_response(result)


@router.put("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: UUID,
    body: ClientUpdateRequest,
    actor: str = Depends(_actor),
    client_repo: ClientRepositoryPort = Depends(get_client_repo),
    audit_repo: AuditLogRepositoryPort = Depends(get_audit_repo),
):
    uc = UpdateClientUseCase(client_repo, audit_repo)
    dto = UpdateClientDTO(
        full_name=body.full_name,
        phone=body.phone,
        email=body.email,
        address=body.address,
        notes=body.notes,
        client_type=body.client_type,
        whatsapp_opt_in=body.whatsapp_opt_in,
        is_active=body.is_active,
    )
    try:
        result = await uc.execute(client_id, dto, actor=actor)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except AlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return _client_to_response(result)


@router.post("/{client_id}/tags", response_model=ClientResponse)
async def add_tag(
    client_id: UUID,
    body: TagRequest,
    actor: str = Depends(_actor),
    client_repo: ClientRepositoryPort = Depends(get_client_repo),
    audit_repo: AuditLogRepositoryPort = Depends(get_audit_repo),
):
    """Agrega un tag CRM al cliente."""
    uc = AddTagUseCase(client_repo, audit_repo)
    try:
        result = await uc.execute(client_id, body.tag, actor=actor)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return _client_to_response(result)


@router.delete("/{client_id}/tags/{tag}", response_model=ClientResponse)
async def remove_tag(
    client_id: UUID,
    tag: str,
    actor: str = Depends(_actor),
    client_repo: ClientRepositoryPort = Depends(get_client_repo),
    audit_repo: AuditLogRepositoryPort = Depends(get_audit_repo),
):
    """Elimina un tag CRM del cliente."""
    uc = RemoveTagUseCase(client_repo, audit_repo)
    try:
        result = await uc.execute(client_id, tag, actor=actor)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return _client_to_response(result)
