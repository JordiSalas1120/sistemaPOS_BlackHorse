from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.ports.repositories.client_repository_port import ClientRepositoryPort
from src.domain.models.client import Client
from src.domain.models.enums import ClientType
from src.infrastructure.database.orm_models.client_orm import ClientORM


class ClientRepository(ClientRepositoryPort):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, id: UUID) -> Client | None:
        result = await self._session.get(ClientORM, id)
        return self._to_domain(result) if result else None

    async def get_by_phone(self, phone: str) -> Client | None:
        stmt = select(ClientORM).where(ClientORM.phone == phone)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def get_by_email(self, email: str) -> Client | None:
        stmt = select(ClientORM).where(ClientORM.email == email)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def list_all(
        self,
        active_only: bool = True,
        client_type: str | None = None,
        tag: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Client]:
        stmt = select(ClientORM)
        if active_only:
            stmt = stmt.where(ClientORM.is_active == True)  # noqa: E712
        if client_type:
            stmt = stmt.where(ClientORM.client_type == client_type)
        if tag:
            stmt = stmt.where(ClientORM.tags.contains([tag]))
        stmt = stmt.order_by(ClientORM.full_name).offset(skip).limit(limit)
        result = await self._session.execute(stmt)
        return [self._to_domain(r) for r in result.scalars().all()]

    async def count(
        self,
        active_only: bool = True,
        client_type: str | None = None,
        tag: str | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(ClientORM)
        if active_only:
            stmt = stmt.where(ClientORM.is_active == True)  # noqa: E712
        if client_type:
            stmt = stmt.where(ClientORM.client_type == client_type)
        if tag:
            stmt = stmt.where(ClientORM.tags.contains([tag]))
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def create(self, client: Client) -> Client:
        orm = self._to_orm(client)
        self._session.add(orm)
        await self._session.flush()
        return client

    async def update(self, client: Client) -> Client:
        orm = await self._session.get(ClientORM, client.id)
        if orm:
            orm.full_name = client.full_name
            orm.phone = client.phone
            orm.email = client.email
            orm.address = client.address
            orm.client_type = client.client_type
            orm.tags = client.tags
            orm.notes = client.notes
            orm.whatsapp_opt_in = client.whatsapp_opt_in
            orm.is_active = client.is_active
            orm.last_purchase_at = client.last_purchase_at
            await self._session.flush()
        return client

    @staticmethod
    def _to_domain(orm: ClientORM) -> Client:
        return Client(
            id=orm.id,
            full_name=orm.full_name,
            phone=orm.phone,
            email=orm.email,
            address=orm.address,
            client_type=ClientType(orm.client_type),
            tags=list(orm.tags or []),
            notes=orm.notes,
            whatsapp_opt_in=orm.whatsapp_opt_in,
            is_active=orm.is_active,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            last_purchase_at=orm.last_purchase_at,
        )

    @staticmethod
    def _to_orm(client: Client) -> ClientORM:
        return ClientORM(
            id=client.id,
            full_name=client.full_name,
            phone=client.phone,
            email=client.email,
            address=client.address,
            client_type=client.client_type,
            tags=client.tags,
            notes=client.notes,
            whatsapp_opt_in=client.whatsapp_opt_in,
            is_active=client.is_active,
        )
