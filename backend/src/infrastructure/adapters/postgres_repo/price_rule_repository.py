from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.ports.repositories.price_rule_repository_port import PriceRuleRepositoryPort
from src.domain.models.enums import ClientType, DiscountType, PriceRuleType
from src.domain.models.price_rule import PriceRule
from src.infrastructure.database.orm_models.price_rule_orm import PriceRuleORM


class PriceRuleRepository(PriceRuleRepositoryPort):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, id: UUID) -> PriceRule | None:
        result = await self._session.get(PriceRuleORM, id)
        return self._to_domain(result) if result else None

    async def list_active(self) -> list[PriceRule]:
        stmt = (
            select(PriceRuleORM)
            .where(PriceRuleORM.is_active == True)  # noqa: E712
            .order_by(PriceRuleORM.priority.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(r) for r in result.scalars().all()]

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[PriceRule]:
        stmt = (
            select(PriceRuleORM)
            .order_by(PriceRuleORM.priority.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(r) for r in result.scalars().all()]

    async def create(self, rule: PriceRule) -> PriceRule:
        orm = self._to_orm(rule)
        self._session.add(orm)
        await self._session.flush()
        return rule

    async def update(self, rule: PriceRule) -> PriceRule:
        orm = await self._session.get(PriceRuleORM, rule.id)
        if orm:
            orm.name = rule.name
            orm.rule_type = rule.rule_type
            orm.client_type_trigger = rule.client_type_trigger
            orm.category_id = rule.category_id
            orm.product_id = rule.product_id
            orm.min_quantity = rule.min_quantity
            orm.discount_type = rule.discount_type
            orm.discount_value = rule.discount_value
            orm.priority = rule.priority
            orm.is_active = rule.is_active
            orm.valid_from = rule.valid_from
            orm.valid_until = rule.valid_until
            await self._session.flush()
        return rule

    async def delete(self, id: UUID) -> None:
        orm = await self._session.get(PriceRuleORM, id)
        if orm:
            await self._session.delete(orm)
            await self._session.flush()

    @staticmethod
    def _to_domain(orm: PriceRuleORM) -> PriceRule:
        return PriceRule(
            id=orm.id,
            name=orm.name,
            rule_type=PriceRuleType(orm.rule_type),
            discount_type=DiscountType(orm.discount_type),
            discount_value=orm.discount_value,
            priority=orm.priority,
            is_active=orm.is_active,
            created_at=orm.created_at,
            client_type_trigger=ClientType(orm.client_type_trigger) if orm.client_type_trigger else None,
            category_id=orm.category_id,
            product_id=orm.product_id,
            min_quantity=orm.min_quantity,
            valid_from=orm.valid_from,
            valid_until=orm.valid_until,
        )

    @staticmethod
    def _to_orm(rule: PriceRule) -> PriceRuleORM:
        return PriceRuleORM(
            id=rule.id,
            name=rule.name,
            rule_type=rule.rule_type,
            client_type_trigger=rule.client_type_trigger,
            category_id=rule.category_id,
            product_id=rule.product_id,
            min_quantity=rule.min_quantity,
            discount_type=rule.discount_type,
            discount_value=rule.discount_value,
            priority=rule.priority,
            is_active=rule.is_active,
            valid_from=rule.valid_from,
            valid_until=rule.valid_until,
        )
