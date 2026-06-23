import uuid
from datetime import datetime, timezone  # noqa: F401  (reservado para extensiones)
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.application.dtos.bom_dto import (
    BOMItemInputDTO,
    CreateBOMDTO,
    UpdateBOMDTO,
)
from src.application.exceptions import (
    AlreadyExistsError,
    BusinessRuleViolation,
    NotFoundError,
)
from src.application.use_cases.workshop.create_bom import CreateBOMUseCase
from src.application.use_cases.workshop.get_bom import GetBOMUseCase
from src.application.use_cases.workshop.list_workshop_products import ListWorkshopProductsUseCase
from src.application.use_cases.workshop.update_bom import UpdateBOMUseCase
from src.dependencies import get_bom_repo, get_product_repo, get_workshop_repo
from src.domain.models.bom import BOMItem
from src.domain.models.enums import ProductType
from src.infrastructure.api.v1.schemas.bom_schema import (
    BOMCreateRequest,
    BOMItemAddRequest,
    BOMItemResponse,
    BOMItemUpdateRequest,
    BOMResponse,
    BOMUpdateRequest,
    BOMWithCostResponse,
)
from src.infrastructure.api.v1.schemas.workshop_schema import (
    WorkshopProductListResponse,
    WorkshopProductResponse,
)

router = APIRouter(prefix="/workshop", tags=["Taller"])


def _not_found(exc: NotFoundError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


def _conflict(exc: AlreadyExistsError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


def _unprocessable(exc: BusinessRuleViolation) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


# ── Materias primas ──────────────────────────────────────────────────────────

@router.get(
    "/materials",
    response_model=WorkshopProductListResponse,
    summary="Listar materias primas",
    description="Retorna productos de tipo `raw_material` con filtros opcionales.",
)
async def list_materials(
    category_id: UUID | None = Query(None, description="Filtrar por categoría"),
    search: str | None = Query(None, description="Búsqueda parcial en nombre o SKU"),
    active_only: bool = Query(True),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    workshop_repo=Depends(get_workshop_repo),
):
    uc = ListWorkshopProductsUseCase(workshop_repo)
    result = await uc.execute(
        product_type=ProductType.RAW_MATERIAL,
        skip=skip, limit=limit,
        category_id=category_id, search=search, active_only=active_only,
    )
    return WorkshopProductListResponse(
        items=[WorkshopProductResponse(**item.__dict__) for item in result.items],
        total=result.total, skip=result.skip, limit=result.limit,
        product_type=result.product_type,
    )


# ── Productos terminados ─────────────────────────────────────────────────────

@router.get(
    "/finished-products",
    response_model=WorkshopProductListResponse,
    summary="Listar productos terminados",
)
async def list_finished_products(
    category_id: UUID | None = Query(None),
    search: str | None = Query(None),
    active_only: bool = Query(True),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    workshop_repo=Depends(get_workshop_repo),
):
    uc = ListWorkshopProductsUseCase(workshop_repo)
    result = await uc.execute(
        product_type=ProductType.FINISHED_PRODUCT,
        skip=skip, limit=limit,
        category_id=category_id, search=search, active_only=active_only,
    )
    return WorkshopProductListResponse(
        items=[WorkshopProductResponse(**item.__dict__) for item in result.items],
        total=result.total, skip=result.skip, limit=result.limit,
        product_type=result.product_type,
    )


# ── BOM ──────────────────────────────────────────────────────────────────────

@router.get(
    "/bom/{product_id}",
    response_model=BOMWithCostResponse,
    summary="Obtener BOM de un producto terminado",
    responses={404: {"description": "Producto o BOM no encontrado"}},
)
async def get_bom(
    product_id: UUID,
    bom_repo=Depends(get_bom_repo),
    product_repo=Depends(get_product_repo),
):
    uc = GetBOMUseCase(bom_repo, product_repo)
    try:
        dto = await uc.execute(product_id)
    except NotFoundError as exc:
        raise _not_found(exc)

    return BOMWithCostResponse(
        id=dto.id,
        finished_product_id=dto.finished_product_id,
        output_quantity=dto.output_quantity,
        is_active=dto.is_active,
        labor_minutes=dto.labor_minutes,
        notes=dto.notes,
        items=[BOMItemResponse(**item.__dict__) for item in dto.items],
        total_material_cost=dto.total_material_cost,
        cost_per_unit=dto.cost_per_unit,
        material_names={str(k): v for k, v in dto.material_names.items()},
    )


@router.post(
    "/bom/{product_id}",
    response_model=BOMResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear BOM para un producto terminado",
    responses={
        404: {"description": "Producto o material no encontrado"},
        409: {"description": "Ya existe una BOM activa para este producto"},
        422: {"description": "Producto no es finished_product o material no es raw_material/supply"},
    },
)
async def create_bom(
    product_id: UUID,
    body: BOMCreateRequest,
    bom_repo=Depends(get_bom_repo),
    product_repo=Depends(get_product_repo),
):
    uc = CreateBOMUseCase(bom_repo, product_repo)
    dto = CreateBOMDTO(
        output_quantity=body.output_quantity,
        labor_minutes=body.labor_minutes,
        notes=body.notes,
        items=[
            BOMItemInputDTO(
                material_id=i.material_id,
                quantity_required=i.quantity_required,
                scrap_factor=i.scrap_factor,
                notes=i.notes,
            )
            for i in body.items
        ],
    )
    try:
        result = await uc.execute(product_id, dto)
    except NotFoundError as exc:
        raise _not_found(exc)
    except AlreadyExistsError as exc:
        raise _conflict(exc)
    except BusinessRuleViolation as exc:
        raise _unprocessable(exc)

    return BOMResponse(
        id=result.id,
        finished_product_id=result.finished_product_id,
        output_quantity=result.output_quantity,
        is_active=result.is_active,
        labor_minutes=result.labor_minutes,
        notes=result.notes,
        items=[BOMItemResponse(**item.__dict__) for item in result.items],
    )


@router.put(
    "/bom/{product_id}",
    response_model=BOMResponse,
    summary="Reemplazar BOM completo de un producto terminado",
    responses={
        404: {"description": "BOM o material no encontrado"},
        422: {"description": "Material no es raw_material/supply"},
    },
)
async def update_bom(
    product_id: UUID,
    body: BOMUpdateRequest,
    bom_repo=Depends(get_bom_repo),
    product_repo=Depends(get_product_repo),
):
    uc = UpdateBOMUseCase(bom_repo, product_repo)
    dto = UpdateBOMDTO(
        output_quantity=body.output_quantity,
        labor_minutes=body.labor_minutes,
        notes=body.notes,
        is_active=body.is_active,
        items=[
            BOMItemInputDTO(
                material_id=i.material_id,
                quantity_required=i.quantity_required,
                scrap_factor=i.scrap_factor,
                notes=i.notes,
            )
            for i in body.items
        ] if body.items is not None else None,
    )
    try:
        result = await uc.execute(product_id, dto)
    except NotFoundError as exc:
        raise _not_found(exc)
    except BusinessRuleViolation as exc:
        raise _unprocessable(exc)

    return BOMResponse(
        id=result.id,
        finished_product_id=result.finished_product_id,
        output_quantity=result.output_quantity,
        is_active=result.is_active,
        labor_minutes=result.labor_minutes,
        notes=result.notes,
        items=[BOMItemResponse(**item.__dict__) for item in result.items],
    )


@router.post(
    "/bom/{product_id}/items",
    response_model=BOMItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Agregar un material a la receta",
    responses={
        404: {"description": "BOM o material no encontrado"},
        409: {"description": "El material ya existe en esta receta"},
        422: {"description": "Material no es raw_material/supply"},
    },
)
async def add_bom_item(
    product_id: UUID,
    body: BOMItemAddRequest,
    bom_repo=Depends(get_bom_repo),
    product_repo=Depends(get_product_repo),
):
    bom = await bom_repo.get_bom_by_product_id(product_id)
    if not bom:
        raise HTTPException(404, "BOM no encontrada para este producto")

    material = await product_repo.get_by_id(body.material_id)
    if not material:
        raise HTTPException(404, f"Material {body.material_id} no encontrado")
    if material.product_type not in (ProductType.RAW_MATERIAL, ProductType.SUPPLY):
        raise HTTPException(
            422,
            f"'{material.name}' no puede usarse como material (tipo: {material.product_type})",
        )

    try:
        item = await bom_repo.add_bom_item(BOMItem(
            id=uuid.uuid4(),
            bom_id=bom.id,
            material_id=body.material_id,
            quantity_required=body.quantity_required,
            scrap_factor=body.scrap_factor,
            notes=body.notes,
            sort_order=0,
        ))
    except AlreadyExistsError as exc:
        raise _conflict(exc)

    return BOMItemResponse(
        id=item.id,
        bom_id=item.bom_id,
        material_id=item.material_id,
        quantity_required=item.quantity_required,
        scrap_factor=item.scrap_factor,
        effective_quantity=item.effective_quantity,
        sort_order=item.sort_order,
        notes=item.notes,
    )


@router.put(
    "/bom/{product_id}/items/{item_id}",
    response_model=BOMItemResponse,
    summary="Editar un item de la receta",
)
async def update_bom_item(
    product_id: UUID,
    item_id: UUID,
    body: BOMItemUpdateRequest,
    bom_repo=Depends(get_bom_repo),
):
    bom = await bom_repo.get_bom_by_product_id(product_id)
    if bom is None:
        raise HTTPException(404, "BOM no encontrada")

    _, items = await bom_repo.get_bom_with_items(bom.id)
    existing_item = next((i for i in items if i.id == item_id), None)
    if not existing_item:
        raise HTTPException(404, f"Item {item_id} no encontrado en esta receta")

    if body.quantity_required is not None:
        existing_item.quantity_required = body.quantity_required
    if body.scrap_factor is not None:
        existing_item.scrap_factor = body.scrap_factor
    if body.notes is not None:
        existing_item.notes = body.notes
    if body.sort_order is not None:
        existing_item.sort_order = body.sort_order

    try:
        updated = await bom_repo.update_bom_item(existing_item)
    except NotFoundError as exc:
        raise _not_found(exc)

    return BOMItemResponse(
        id=updated.id,
        bom_id=updated.bom_id,
        material_id=updated.material_id,
        quantity_required=updated.quantity_required,
        scrap_factor=updated.scrap_factor,
        effective_quantity=updated.effective_quantity,
        sort_order=updated.sort_order,
        notes=updated.notes,
    )


@router.delete(
    "/bom/{product_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un material de la receta",
)
async def delete_bom_item(
    product_id: UUID,
    item_id: UUID,
    bom_repo=Depends(get_bom_repo),
):
    try:
        await bom_repo.remove_bom_item(item_id)
    except NotFoundError as exc:
        raise _not_found(exc)
