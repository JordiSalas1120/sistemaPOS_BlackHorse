from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.ports.repositories.audit_log_repository_port import AuditLogRepositoryPort
from src.domain.models.audit_log import AuditLog
from src.domain.models.enums import AuditAction
from src.infrastructure.database.orm_models.audit_log_orm import AuditLogORM


class AuditLogRepository(AuditLogRepositoryPort):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, log: AuditLog) -> AuditLog:
        orm = AuditLogORM(
            id=log.id,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            action=log.action,
            actor=log.actor,
            payload=log.payload,
            ip_address=log.ip_address,
        )
        self._session.add(orm)
        await self._session.flush()
        return log

    async def list_by_entity(
        self, entity_type: str, entity_id: UUID, skip: int = 0, limit: int = 50
    ) -> list[AuditLog]:
        stmt = (
            select(AuditLogORM)
            .where(
                AuditLogORM.entity_type == entity_type,
                AuditLogORM.entity_id == entity_id,
            )
            .order_by(AuditLogORM.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(r) for r in result.scalars().all()]

    async def list_recent(self, skip: int = 0, limit: int = 50) -> list[AuditLog]:
        stmt = (
            select(AuditLogORM)
            .order_by(AuditLogORM.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(r) for r in result.scalars().all()]

    @staticmethod
    def _to_domain(orm: AuditLogORM) -> AuditLog:
        return AuditLog(
            id=orm.id,
            entity_type=orm.entity_type,
            entity_id=orm.entity_id,
            action=AuditAction(orm.action),
            actor=orm.actor,
            payload=orm.payload or {},
            ip_address=orm.ip_address,
            created_at=orm.created_at,
        )
