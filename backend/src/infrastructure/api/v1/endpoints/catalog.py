from fastapi import APIRouter, Depends, HTTPException, Query

from src.application.ports.repositories.catalog_repository_port import CatalogRepositoryPort
from src.config import settings
from src.dependencies import get_catalog_repo
from src.infrastructure.api.v1.schemas.catalog_schema import (
    CatalogCategoryResponse,
    CatalogImageResponse,
    CatalogProductListResponse,
    CatalogProductResponse,
)

router = APIRouter(tags=["Catálogo Público"])


def _to_product_response(p) -> CatalogProductResponse:
    """Convierte CatalogProduct a schema de respuesta, aplicando CATALOG_SHOW_PRICES."""
    return CatalogProductResponse(
        id=p.id,
        sku=p.sku,
        name=p.name,
        description=p.description,
        category_id=p.category_id,
        category_name=p.category_name,
        category_slug=p.category_slug,
        unit=p.unit,
        attributes=p.attributes,
        images=[
            CatalogImageResponse(
                id=img.id,
                url=img.url,
                alt_text=img.alt_text,
                sort_order=img.sort_order,
                is_primary=img.is_primary,
            )
            for img in p.images
        ],
        base_price=p.base_price if settings.catalog_show_prices else None,
    )


@router.get(
    "/products",
    response_model=CatalogProductListResponse,
    summary="Listar productos del catálogo público",
    description=(
        "Lista paginada de productos activos y visibles en catálogo. "
        "No requiere autenticación. No expone precios mayoristas ni datos internos."
    ),
)
async def list_catalog_products(
    category_slug: str | None = Query(None, description="Filtrar por slug de categoría"),
    search: str | None = Query(None, description="Búsqueda en nombre y descripción"),
    skip: int = Query(0, ge=0, description="Offset de paginación"),
    limit: int = Query(24, ge=1, le=100, description="Máximo de resultados (máx. 100)"),
    catalog_repo: CatalogRepositoryPort = Depends(get_catalog_repo),
):
    products, total = await catalog_repo.list_catalog_products(
        category_slug=category_slug,
        search=search,
        skip=skip,
        limit=limit,
    )
    return CatalogProductListResponse(
        items=[_to_product_response(p) for p in products],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/products/{sku}",
    response_model=CatalogProductResponse,
    summary="Detalle de producto por SKU",
    responses={404: {"description": "Producto no encontrado o no visible en catálogo"}},
)
async def get_catalog_product(
    sku: str,
    catalog_repo: CatalogRepositoryPort = Depends(get_catalog_repo),
):
    product = await catalog_repo.get_catalog_product_by_sku(sku.upper())
    if product is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado en el catálogo")
    return _to_product_response(product)


@router.get(
    "/categories",
    response_model=list[CatalogCategoryResponse],
    summary="Categorías con productos en catálogo",
    description="Solo retorna categorías que tienen al menos un producto activo visible en catálogo.",
)
async def list_catalog_categories(
    catalog_repo: CatalogRepositoryPort = Depends(get_catalog_repo),
):
    categories = await catalog_repo.list_catalog_categories()
    return [
        CatalogCategoryResponse(
            id=cat.id,
            name=cat.name,
            slug=cat.slug,
            description=cat.description,
            product_count=cat.product_count,
        )
        for cat in categories
    ]


@router.get(
    "/products/{sku}/related",
    response_model=list[CatalogProductResponse],
    summary="Productos relacionados",
    description="Hasta 4 productos de la misma categoría, excluyendo el producto actual.",
)
async def get_related_products(
    sku: str,
    catalog_repo: CatalogRepositoryPort = Depends(get_catalog_repo),
):
    product = await catalog_repo.get_catalog_product_by_sku(sku.upper())
    if product is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    related = await catalog_repo.get_related_products(
        product_id=product.id,
        category_id=product.category_id,
        limit=4,
    )
    return [_to_product_response(p) for p in related]
