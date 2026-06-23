from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from src.application.dtos.sale_dto import CreateSaleDTO, SaleItemInputDTO
from src.application.exceptions import BusinessRuleViolation, NotFoundError
from src.application.ports.repositories.audit_log_repository_port import AuditLogRepositoryPort
from src.application.ports.repositories.category_repository_port import CategoryRepositoryPort
from src.application.ports.repositories.client_repository_port import ClientRepositoryPort
from src.application.ports.repositories.inventory_repository_port import InventoryRepositoryPort
from src.application.ports.repositories.price_rule_repository_port import PriceRuleRepositoryPort
from src.application.ports.repositories.product_repository_port import ProductRepositoryPort
from src.application.ports.repositories.sale_repository_port import SaleRepositoryPort
from src.application.use_cases.sales.cancel_sale import CancelSaleUseCase
from src.application.use_cases.sales.create_sale import CreateSaleUseCase
from src.application.use_cases.sales.get_sale import GetSaleUseCase
from src.application.use_cases.sales.list_sales import ListSalesUseCase
from src.dependencies import (
    get_audit_repo,
    get_category_repo,
    get_client_repo,
    get_crm_tagging_service,
    get_inventory_repo,
    get_inventory_service,
    get_price_rule_repo,
    get_pricing_service,
    get_product_repo,
    get_sale_repo,
)
from src.domain.models.enums import SaleStatus
from src.domain.services.crm_tagging_service import CrmTaggingService
from src.domain.services.inventory_service import InventoryService
from src.domain.services.pricing_service import PricingService
from src.infrastructure.api.v1.schemas.common_schema import MessageResponse
from src.infrastructure.api.v1.schemas.sale_schema import (
    CreateSaleRequest,
    SaleItemResponse,
    SaleListResponse,
    SaleResponse,
)

router = APIRouter(prefix="/sales", tags=["Ventas"])


def _actor(x_actor: str = Header(default="api")) -> str:
    return x_actor


def _sale_to_response(dto) -> SaleResponse:
    items = [SaleItemResponse(**item.__dict__) for item in dto.items]
    data = {**dto.__dict__, "items": items}
    return SaleResponse(**data)


@router.get("", response_model=SaleListResponse, summary="Listar ventas")
async def list_sales(
    client_id: UUID | None = Query(None, description="Filtrar por cliente"),
    status: SaleStatus | None = Query(None, description="Filtrar por estado: draft | completed | cancelled | refunded"),
    date_from: datetime | None = Query(None, description="Fecha inicio (ISO 8601 UTC), ej: 2026-01-01T00:00:00Z"),
    date_to: datetime | None = Query(None, description="Fecha fin (ISO 8601 UTC), ej: 2026-12-31T23:59:59Z"),
    skip: int = Query(0, ge=0, description="Registros a omitir (paginación)"),
    limit: int = Query(50, ge=1, le=200, description="Máximo de registros a retornar"),
    sale_repo: SaleRepositoryPort = Depends(get_sale_repo),
    product_repo: ProductRepositoryPort = Depends(get_product_repo),
):
    uc = ListSalesUseCase(sale_repo, product_repo)
    result = await uc.execute(
        client_id=client_id, status=status, date_from=date_from, date_to=date_to,
        skip=skip, limit=limit
    )
    return SaleListResponse(
        items=[_sale_to_response(s) for s in result.items],
        total=result.total,
        skip=result.skip,
        limit=result.limit,
    )


@router.post(
    "",
    response_model=SaleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar venta (POS)",
    description="""
Crea una venta aplicando automáticamente:

- **Motor de precios**: selecciona la regla activa de mayor prioridad según tipo de cliente, cantidad y categoría
- **Descuento de stock**: deduce las unidades vendidas del inventario
- **Etiquetado CRM**: agrega tags `mayorista` y/o `recordatorio_mantenimiento` según corresponda

La numeración se genera automáticamente en formato `VTA-YYYY-NNNNN`.
""",
)
async def create_sale(
    body: CreateSaleRequest,
    actor: str = Depends(_actor),
    sale_repo: SaleRepositoryPort = Depends(get_sale_repo),
    product_repo: ProductRepositoryPort = Depends(get_product_repo),
    inventory_repo: InventoryRepositoryPort = Depends(get_inventory_repo),
    client_repo: ClientRepositoryPort = Depends(get_client_repo),
    category_repo: CategoryRepositoryPort = Depends(get_category_repo),
    price_rule_repo: PriceRuleRepositoryPort = Depends(get_price_rule_repo),
    audit_repo: AuditLogRepositoryPort = Depends(get_audit_repo),
    pricing_service: PricingService = Depends(get_pricing_service),
    inventory_service: InventoryService = Depends(get_inventory_service),
    crm_tagging_service: CrmTaggingService = Depends(get_crm_tagging_service),
):
    uc = CreateSaleUseCase(
        sale_repo=sale_repo,
        product_repo=product_repo,
        inventory_repo=inventory_repo,
        client_repo=client_repo,
        category_repo=category_repo,
        price_rule_repo=price_rule_repo,
        audit_repo=audit_repo,
        pricing_service=pricing_service,
        inventory_service=inventory_service,
        crm_tagging_service=crm_tagging_service,
    )
    dto = CreateSaleDTO(
        items=[SaleItemInputDTO(product_id=i.product_id, quantity=i.quantity) for i in body.items],
        payment_type=body.payment_type,
        sale_type=body.sale_type,
        client_id=body.client_id,
        notes=body.notes,
    )
    try:
        result = await uc.execute(dto, actor=actor)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BusinessRuleViolation as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    return _sale_to_response(result)


@router.get("/{sale_id}", response_model=SaleResponse)
async def get_sale(
    sale_id: UUID,
    sale_repo: SaleRepositoryPort = Depends(get_sale_repo),
    product_repo: ProductRepositoryPort = Depends(get_product_repo),
):
    uc = GetSaleUseCase(sale_repo, product_repo)
    try:
        result = await uc.execute(sale_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return _sale_to_response(result)


@router.post(
    "/{sale_id}/cancel",
    response_model=MessageResponse,
    summary="Cancelar venta",
    description="Cancela una venta en estado `completed` o `draft` y devuelve el stock automáticamente.",
)
async def cancel_sale(
    sale_id: UUID,
    actor: str = Depends(_actor),
    sale_repo: SaleRepositoryPort = Depends(get_sale_repo),
    inventory_repo: InventoryRepositoryPort = Depends(get_inventory_repo),
    product_repo: ProductRepositoryPort = Depends(get_product_repo),
    audit_repo: AuditLogRepositoryPort = Depends(get_audit_repo),
    inventory_service: InventoryService = Depends(get_inventory_service),
):
    uc = CancelSaleUseCase(sale_repo, inventory_repo, product_repo, audit_repo, inventory_service)
    try:
        await uc.execute(sale_id, actor=actor)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BusinessRuleViolation as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    return MessageResponse(message="Venta cancelada correctamente")
