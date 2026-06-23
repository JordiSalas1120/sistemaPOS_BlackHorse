from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from src.application.dtos.price_rule_dto import CreatePriceRuleDTO
from src.application.exceptions import NotFoundError
from src.application.ports.repositories.price_rule_repository_port import PriceRuleRepositoryPort
from src.application.use_cases.price_rules.manage_price_rules import (
    CreatePriceRuleUseCase,
    DeletePriceRuleUseCase,
    ListPriceRulesUseCase,
    TogglePriceRuleUseCase,
)
from src.dependencies import get_price_rule_repo
from src.infrastructure.api.v1.schemas.common_schema import MessageResponse
from src.infrastructure.api.v1.schemas.price_rule_schema import (
    PriceRuleCreateRequest,
    PriceRuleResponse,
)

router = APIRouter(prefix="/price-rules", tags=["Reglas de precios"])


def _to_response(dto) -> PriceRuleResponse:
    return PriceRuleResponse(**dto.__dict__)


@router.get("", response_model=list[PriceRuleResponse])
async def list_price_rules(
    repo: PriceRuleRepositoryPort = Depends(get_price_rule_repo),
):
    uc = ListPriceRulesUseCase(repo)
    rules = await uc.execute()
    return [_to_response(r) for r in rules]


@router.post("", response_model=PriceRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_price_rule(
    body: PriceRuleCreateRequest,
    repo: PriceRuleRepositoryPort = Depends(get_price_rule_repo),
):
    uc = CreatePriceRuleUseCase(repo)
    dto = CreatePriceRuleDTO(
        name=body.name,
        rule_type=body.rule_type,
        discount_type=body.discount_type,
        discount_value=body.discount_value,
        priority=body.priority,
        client_type_trigger=body.client_type_trigger,
        category_id=body.category_id,
        product_id=body.product_id,
        min_quantity=body.min_quantity,
        valid_from=body.valid_from,
        valid_until=body.valid_until,
    )
    result = await uc.execute(dto)
    return _to_response(result)


@router.patch("/{rule_id}/toggle", response_model=PriceRuleResponse)
async def toggle_price_rule(
    rule_id: UUID,
    is_active: bool,
    repo: PriceRuleRepositoryPort = Depends(get_price_rule_repo),
):
    uc = TogglePriceRuleUseCase(repo)
    try:
        result = await uc.execute(rule_id, is_active)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return _to_response(result)


@router.delete("/{rule_id}", response_model=MessageResponse)
async def delete_price_rule(
    rule_id: UUID,
    repo: PriceRuleRepositoryPort = Depends(get_price_rule_repo),
):
    uc = DeletePriceRuleUseCase(repo)
    try:
        await uc.execute(rule_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return MessageResponse(message="Regla eliminada correctamente")
