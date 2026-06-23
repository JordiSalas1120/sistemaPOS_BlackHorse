from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from src.application.dtos.inventory_dto import AdjustStockDTO
from src.application.exceptions import InsufficientStockError, NotFoundError
from src.application.ports.repositories.audit_log_repository_port import AuditLogRepositoryPort
from src.application.ports.repositories.inventory_repository_port import InventoryRepositoryPort
from src.application.ports.repositories.product_repository_port import ProductRepositoryPort
from src.application.use_cases.inventory.adjust_stock import AdjustStockUseCase
from src.application.use_cases.inventory.get_inventory_snapshot import (
    GetInventorySnapshotUseCase,
    GetProductMovementsUseCase,
)
from src.application.use_cases.inventory.get_low_stock_alerts import GetLowStockAlertsUseCase
from src.dependencies import (
    get_audit_repo,
    get_inventory_repo,
    get_inventory_service,
    get_product_repo,
)
from src.domain.services.inventory_service import InventoryService
from src.infrastructure.api.v1.schemas.inventory_schema import (
    AdjustStockRequest,
    InventoryItemResponse,
    MovementResponse,
)

router = APIRouter(prefix="/inventory", tags=["Inventario"])


def _actor(x_actor: str = Header(default="api")) -> str:
    return x_actor


@router.get("", response_model=list[InventoryItemResponse])
async def get_inventory_snapshot(
    inventory_repo: InventoryRepositoryPort = Depends(get_inventory_repo),
    product_repo: ProductRepositoryPort = Depends(get_product_repo),
):
    """Estado actual del stock de todos los productos activos."""
    uc = GetInventorySnapshotUseCase(inventory_repo, product_repo)
    items = await uc.execute()
    return [InventoryItemResponse(**item.__dict__) for item in items]


@router.get("/alerts", response_model=list[InventoryItemResponse])
async def get_low_stock_alerts(
    inventory_repo: InventoryRepositoryPort = Depends(get_inventory_repo),
    product_repo: ProductRepositoryPort = Depends(get_product_repo),
):
    """Productos con stock por debajo del umbral mínimo."""
    uc = GetLowStockAlertsUseCase(inventory_repo, product_repo)
    items = await uc.execute()
    return [InventoryItemResponse(**item.__dict__) for item in items]


@router.post(
    "/adjust",
    response_model=MovementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar movimiento de stock",
    description="""
Registra un movimiento de inventario y actualiza el stock del producto.

**Tipos de movimiento:**
- `purchase` — Compra / entrada de mercadería
- `adjustment` — Ajuste manual de inventario
- `return` — Devolución de cliente
- `loss` — Merma, pérdida o daño

Usa `quantity_delta` positivo para entradas y negativo para salidas.
No se permite dejar el stock en negativo.
""",
)
async def adjust_stock(
    body: AdjustStockRequest,
    actor: str = Depends(_actor),
    inventory_repo: InventoryRepositoryPort = Depends(get_inventory_repo),
    product_repo: ProductRepositoryPort = Depends(get_product_repo),
    audit_repo: AuditLogRepositoryPort = Depends(get_audit_repo),
    inventory_service: InventoryService = Depends(get_inventory_service),
):
    """Registra un movimiento de stock (entrada, salida, ajuste, devolución, pérdida)."""
    uc = AdjustStockUseCase(inventory_repo, product_repo, audit_repo, inventory_service)
    dto = AdjustStockDTO(
        product_id=body.product_id,
        quantity_delta=body.quantity_delta,
        movement_type=body.movement_type,
        actor=actor,
        notes=body.notes,
        reference_id=body.reference_id,
    )
    try:
        result = await uc.execute(dto)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InsufficientStockError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    return MovementResponse(**result.__dict__)


@router.get("/{product_id}/movements", response_model=list[MovementResponse])
async def get_product_movements(
    product_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    inventory_repo: InventoryRepositoryPort = Depends(get_inventory_repo),
    product_repo: ProductRepositoryPort = Depends(get_product_repo),
):
    """Historial de movimientos de stock de un producto."""
    uc = GetProductMovementsUseCase(inventory_repo, product_repo)
    try:
        movements = await uc.execute(product_id, skip=skip, limit=limit)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return [MovementResponse(**m.__dict__) for m in movements]
