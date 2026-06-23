from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from src.application.dtos.production_dto import (
    CompleteProductionOrderDTO,
    CreateProductionOrderDTO,
    _to_dto,
)
from src.application.exceptions import BusinessRuleViolation, InsufficientStockError, NotFoundError
from src.application.ports.repositories.inventory_repository_port import InventoryRepositoryPort
from src.application.ports.repositories.production_order_repository_port import (
    ProductionOrderRepositoryPort,
)
from src.application.ports.repositories.product_repository_port import ProductRepositoryPort
from src.application.use_cases.production.cancel_production_order import CancelProductionOrderUseCase
from src.application.use_cases.production.complete_production_order import CompleteProductionOrderUseCase
from src.application.use_cases.production.create_production_order import CreateProductionOrderUseCase
from src.application.use_cases.production.list_production_orders import ListProductionOrdersUseCase
from src.application.use_cases.production.start_production_order import StartProductionOrderUseCase
from src.dependencies import (
    get_bom_repo,
    get_inventory_repo,
    get_product_repo,
    get_production_order_repo,
)
from src.domain.models.enums import ProductionOrderStatus
from src.domain.services.production_cost_service import ProductionCostService
from src.infrastructure.api.v1.schemas.production_schema import (
    CancelProductionOrderRequest,
    CompleteProductionOrderRequest,
    CreateProductionOrderRequest,
    ProductionOrderListResponse,
    ProductionOrderResponse,
)

router = APIRouter(prefix="/workshop/orders", tags=["Taller — Órdenes de Producción"])


def _actor(x_actor: str = Header(default="api")) -> str:
    return x_actor


def _order_to_response(dto) -> ProductionOrderResponse:
    items = [
        {
            "id": i.id, "order_id": i.order_id, "material_id": i.material_id,
            "material_sku": i.material_sku, "material_name": i.material_name,
            "quantity_required": i.quantity_required, "quantity_consumed": i.quantity_consumed,
            "unit_cost_snapshot": i.unit_cost_snapshot, "subtotal_cost": i.subtotal_cost,
            "notes": i.notes,
        }
        for i in dto.items
    ]
    return ProductionOrderResponse(**{**dto.__dict__, "items": items})


def _insufficient_stock(e: InsufficientStockError, code: str) -> HTTPException:
    return HTTPException(
        status_code=409,
        detail={
            "message": str(e),
            "error_code": code,
            "product_id": e.product_id,
            "available": e.available,
            "requested": e.requested,
        },
    )


# GET /workshop/orders
@router.get("", response_model=ProductionOrderListResponse, summary="Listar órdenes de producción")
async def list_orders(
    status: ProductionOrderStatus | None = Query(None, description="Filtrar por estado"),
    finished_product_id: UUID | None = Query(None, description="Filtrar por producto terminado"),
    produced_by: str | None = Query(None, description="Filtrar por artífice"),
    date_from: datetime | None = Query(None, description="Fecha inicio (ISO 8601 UTC)"),
    date_to: datetime | None = Query(None, description="Fecha fin (ISO 8601 UTC)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    order_repo: ProductionOrderRepositoryPort = Depends(get_production_order_repo),
):
    uc = ListProductionOrdersUseCase(order_repo)
    result = await uc.execute(
        status=status, finished_product_id=finished_product_id,
        produced_by=produced_by, date_from=date_from, date_to=date_to,
        skip=skip, limit=limit,
    )
    return ProductionOrderListResponse(
        items=[_order_to_response(o) for o in result.items],
        total=result.total, skip=result.skip, limit=result.limit,
    )


# POST /workshop/orders
@router.post(
    "",
    response_model=ProductionOrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear orden de producción",
)
async def create_order(
    body: CreateProductionOrderRequest,
    actor: str = Depends(_actor),
    order_repo: ProductionOrderRepositoryPort = Depends(get_production_order_repo),
    product_repo: ProductRepositoryPort = Depends(get_product_repo),
    bom_repo=Depends(get_bom_repo),
):
    uc = CreateProductionOrderUseCase(order_repo, product_repo, bom_repo)
    try:
        dto = await uc.execute(
            CreateProductionOrderDTO(
                bom_id=body.bom_id,
                quantity_to_produce=body.quantity_to_produce,
                produced_by=body.produced_by,
                notes=body.notes,
            )
        )
        return _order_to_response(dto)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessRuleViolation as e:
        raise HTTPException(status_code=422, detail=str(e))


# GET /workshop/orders/{order_id}
@router.get("/{order_id}", response_model=ProductionOrderResponse, summary="Detalle de orden")
async def get_order(
    order_id: UUID,
    order_repo: ProductionOrderRepositoryPort = Depends(get_production_order_repo),
    product_repo: ProductRepositoryPort = Depends(get_product_repo),
):
    result = await order_repo.get_order_with_items(order_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Orden {order_id} no encontrada")
    order, items = result

    # Enriquecer con nombres de materiales y del producto terminado
    material_info: dict = {}
    for item in items:
        material = await product_repo.get_by_id(item.material_id)
        if material:
            material_info[item.material_id] = (material.sku, material.name)
    finished = await product_repo.get_by_id(order.finished_product_id)

    dto = _to_dto(
        order,
        items,
        material_info=material_info,
        finished_product_name=finished.name if finished else "",
        finished_product_sku=finished.sku if finished else "",
    )
    return _order_to_response(dto)


# POST /workshop/orders/{order_id}/start
@router.post(
    "/{order_id}/start",
    response_model=ProductionOrderResponse,
    summary="Iniciar orden (valida stock de materiales)",
)
async def start_order(
    order_id: UUID,
    actor: str = Depends(_actor),
    order_repo: ProductionOrderRepositoryPort = Depends(get_production_order_repo),
    inventory_repo: InventoryRepositoryPort = Depends(get_inventory_repo),
):
    uc = StartProductionOrderUseCase(order_repo, inventory_repo)
    try:
        dto = await uc.execute(order_id)
        return _order_to_response(dto)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InsufficientStockError as e:
        raise _insufficient_stock(e, "INSUFFICIENT_STOCK")
    except BusinessRuleViolation as e:
        raise HTTPException(status_code=422, detail=str(e))


# POST /workshop/orders/{order_id}/complete
@router.post(
    "/{order_id}/complete",
    response_model=ProductionOrderResponse,
    summary="Completar orden (descuenta materiales y acredita terminado — transacción atómica)",
)
async def complete_order(
    order_id: UUID,
    body: CompleteProductionOrderRequest,
    actor: str = Depends(_actor),
    order_repo: ProductionOrderRepositoryPort = Depends(get_production_order_repo),
    inventory_repo: InventoryRepositoryPort = Depends(get_inventory_repo),
):
    uc = CompleteProductionOrderUseCase(
        order_repo, inventory_repo, ProductionCostService()
    )
    try:
        dto = await uc.execute(
            order_id,
            CompleteProductionOrderDTO(
                quantity_produced=body.quantity_produced,
                notes=body.notes,
            ),
            actor=actor,
        )
        return _order_to_response(dto)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InsufficientStockError as e:
        raise _insufficient_stock(e, "INSUFFICIENT_STOCK_AT_COMPLETION")
    except BusinessRuleViolation as e:
        raise HTTPException(status_code=422, detail=str(e))


# POST /workshop/orders/{order_id}/cancel
@router.post(
    "/{order_id}/cancel",
    response_model=ProductionOrderResponse,
    summary="Cancelar orden",
)
async def cancel_order(
    order_id: UUID,
    body: CancelProductionOrderRequest,
    actor: str = Depends(_actor),
    order_repo: ProductionOrderRepositoryPort = Depends(get_production_order_repo),
):
    uc = CancelProductionOrderUseCase(order_repo)
    try:
        dto = await uc.execute(order_id, body.reason)
        return _order_to_response(dto)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessRuleViolation as e:
        raise HTTPException(status_code=422, detail=str(e))
