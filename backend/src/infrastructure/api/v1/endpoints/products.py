from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from src.application.dtos.product_dto import CreateProductDTO, UpdateProductDTO
from src.application.exceptions import AlreadyExistsError, NotFoundError
from src.domain.models.enums import ProductType
from src.application.ports.repositories.audit_log_repository_port import AuditLogRepositoryPort
from src.application.ports.repositories.category_repository_port import CategoryRepositoryPort
from src.application.ports.repositories.inventory_repository_port import InventoryRepositoryPort
from src.application.ports.repositories.product_repository_port import ProductRepositoryPort
from src.application.use_cases.products.create_product import CreateProductUseCase
from src.application.use_cases.products.delete_product import DeleteProductUseCase
from src.application.use_cases.products.get_product import GetProductUseCase
from src.application.use_cases.products.list_categories import ListCategoriesUseCase
from src.application.use_cases.products.list_products import ListProductsUseCase
from src.application.use_cases.products.update_product import UpdateProductUseCase
from src.dependencies import get_audit_repo, get_category_repo, get_inventory_repo, get_product_repo
from src.infrastructure.api.v1.schemas.common_schema import MessageResponse, PaginationMeta
from src.infrastructure.api.v1.schemas.product_schema import (
    CategoryResponse,
    ProductCreateRequest,
    ProductListResponse,
    ProductResponse,
    ProductUpdateRequest,
)

router = APIRouter(prefix="/products", tags=["Productos"])
categories_router = APIRouter(prefix="/categories", tags=["Categorías"])


def _actor(x_actor: str = Header(default="api")) -> str:
    """Identifica quién realiza la operación. En el futuro vendrá del token JWT."""
    return x_actor


# ── Categorías ────────────────────────────────────────────────────────────────

@categories_router.get("", response_model=list[CategoryResponse])
async def list_categories(
    category_repo: CategoryRepositoryPort = Depends(get_category_repo),
):
    """Lista las 4 categorías base del catálogo."""
    uc = ListCategoriesUseCase(category_repo)
    categories = await uc.execute()
    return [CategoryResponse(id=c.id, name=c.name, slug=c.slug, description=c.description) for c in categories]


# ── Productos ─────────────────────────────────────────────────────────────────

@router.get("", response_model=ProductListResponse)
async def list_products(
    active_only: bool = Query(True),
    category_id: UUID | None = Query(None),
    product_type: ProductType | None = Query(
        None, description="Filtrar por tipo: raw_material, finished_product, resale, etc."
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    product_repo: ProductRepositoryPort = Depends(get_product_repo),
    category_repo: CategoryRepositoryPort = Depends(get_category_repo),
    inventory_repo: InventoryRepositoryPort = Depends(get_inventory_repo),
):
    uc = ListProductsUseCase(product_repo, category_repo, inventory_repo)
    result = await uc.execute(
        active_only=active_only, category_id=category_id, skip=skip, limit=limit,
        product_type=product_type,
    )
    return ProductListResponse(
        items=[ProductResponse(**item.__dict__) for item in result.items],
        total=result.total,
        skip=result.skip,
        limit=result.limit,
    )


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    body: ProductCreateRequest,
    actor: str = Depends(_actor),
    product_repo: ProductRepositoryPort = Depends(get_product_repo),
    category_repo: CategoryRepositoryPort = Depends(get_category_repo),
    inventory_repo: InventoryRepositoryPort = Depends(get_inventory_repo),
    audit_repo: AuditLogRepositoryPort = Depends(get_audit_repo),
):
    uc = CreateProductUseCase(product_repo, category_repo, inventory_repo, audit_repo)
    dto = CreateProductDTO(
        name=body.name,
        sku=body.sku,
        category_id=body.category_id,
        base_price=body.base_price,
        unit=body.unit,
        description=body.description,
        wholesale_price=body.wholesale_price,
        image_url=body.image_url,
        attributes=body.attributes,
        low_stock_threshold=body.low_stock_threshold,
        product_type=body.product_type,
        show_in_catalog=body.show_in_catalog,
        cost_price=body.cost_price,
    )
    try:
        result = await uc.execute(dto, actor=actor)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except AlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return ProductResponse(**result.__dict__)


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: UUID,
    product_repo: ProductRepositoryPort = Depends(get_product_repo),
    category_repo: CategoryRepositoryPort = Depends(get_category_repo),
    inventory_repo: InventoryRepositoryPort = Depends(get_inventory_repo),
):
    uc = GetProductUseCase(product_repo, category_repo, inventory_repo)
    try:
        result = await uc.execute(product_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return ProductResponse(**result.__dict__)


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: UUID,
    body: ProductUpdateRequest,
    actor: str = Depends(_actor),
    product_repo: ProductRepositoryPort = Depends(get_product_repo),
    category_repo: CategoryRepositoryPort = Depends(get_category_repo),
    inventory_repo: InventoryRepositoryPort = Depends(get_inventory_repo),
    audit_repo: AuditLogRepositoryPort = Depends(get_audit_repo),
):
    uc = UpdateProductUseCase(product_repo, category_repo, inventory_repo, audit_repo)
    dto = UpdateProductDTO(
        name=body.name,
        description=body.description,
        category_id=body.category_id,
        base_price=body.base_price,
        wholesale_price=body.wholesale_price,
        unit=body.unit,
        image_url=body.image_url,
        attributes=body.attributes,
        is_active=body.is_active,
        product_type=body.product_type,
        show_in_catalog=body.show_in_catalog,
        cost_price=body.cost_price,
    )
    try:
        result = await uc.execute(product_id, dto, actor=actor)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return ProductResponse(**result.__dict__)


@router.delete("/{product_id}", response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def delete_product(
    product_id: UUID,
    actor: str = Depends(_actor),
    product_repo: ProductRepositoryPort = Depends(get_product_repo),
    audit_repo: AuditLogRepositoryPort = Depends(get_audit_repo),
):
    """Soft delete: marca el producto como inactivo."""
    uc = DeleteProductUseCase(product_repo, audit_repo)
    try:
        await uc.execute(product_id, actor=actor)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return MessageResponse(message="Producto desactivado correctamente")
