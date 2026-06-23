"""
CRUD de reglas de precios en un solo archivo dado que la lógica es sencilla.
"""
import uuid
from datetime import datetime, timezone
from uuid import UUID

from src.application.dtos.price_rule_dto import CreatePriceRuleDTO, PriceRuleDTO
from src.application.exceptions import NotFoundError
from src.application.ports.repositories.price_rule_repository_port import PriceRuleRepositoryPort
from src.domain.models.price_rule import PriceRule


def _to_dto(r: PriceRule) -> PriceRuleDTO:
    return PriceRuleDTO(
        id=r.id,
        name=r.name,
        rule_type=r.rule_type,
        discount_type=r.discount_type,
        discount_value=r.discount_value,
        priority=r.priority,
        is_active=r.is_active,
        created_at=r.created_at,
        client_type_trigger=r.client_type_trigger,
        category_id=r.category_id,
        product_id=r.product_id,
        min_quantity=r.min_quantity,
        valid_from=r.valid_from,
        valid_until=r.valid_until,
    )


class ListPriceRulesUseCase:
    def __init__(self, repo: PriceRuleRepositoryPort):
        self._repo = repo

    async def execute(self, skip: int = 0, limit: int = 100) -> list[PriceRuleDTO]:
        rules = await self._repo.list_all(skip=skip, limit=limit)
        return [_to_dto(r) for r in rules]


class CreatePriceRuleUseCase:
    def __init__(self, repo: PriceRuleRepositoryPort):
        self._repo = repo

    async def execute(self, dto: CreatePriceRuleDTO) -> PriceRuleDTO:
        now = datetime.now(timezone.utc)
        rule = PriceRule(
            id=uuid.uuid4(),
            name=dto.name,
            rule_type=dto.rule_type,
            discount_type=dto.discount_type,
            discount_value=dto.discount_value,
            priority=dto.priority,
            is_active=True,
            created_at=now,
            client_type_trigger=dto.client_type_trigger,
            category_id=dto.category_id,
            product_id=dto.product_id,
            min_quantity=dto.min_quantity,
            valid_from=dto.valid_from,
            valid_until=dto.valid_until,
        )
        saved = await self._repo.create(rule)
        return _to_dto(saved)


class TogglePriceRuleUseCase:
    """Activa o desactiva una regla de precio."""

    def __init__(self, repo: PriceRuleRepositoryPort):
        self._repo = repo

    async def execute(self, rule_id: UUID, is_active: bool) -> PriceRuleDTO:
        rule = await self._repo.get_by_id(rule_id)
        if not rule:
            raise NotFoundError("Regla de precio", str(rule_id))
        rule.is_active = is_active
        saved = await self._repo.update(rule)
        return _to_dto(saved)


class DeletePriceRuleUseCase:
    def __init__(self, repo: PriceRuleRepositoryPort):
        self._repo = repo

    async def execute(self, rule_id: UUID) -> None:
        rule = await self._repo.get_by_id(rule_id)
        if not rule:
            raise NotFoundError("Regla de precio", str(rule_id))
        await self._repo.delete(rule_id)
