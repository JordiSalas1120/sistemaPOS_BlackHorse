from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.ports.repositories.workshop_product_repository_port import (
    WorkshopProductRepositoryPort,
)
from src.domain.models.enums import ProductType
from src.domain.models.product import Product
from src.infrastructure.adapters.postgres_repo.product_repository import ProductRepository
from src.infrastructure.database.orm_models.product_orm import ProductORM


class WorkshopProductRepository(ProductRepository, WorkshopProductRepositoryPort):
    """
    Consultas específicas del taller sobre la tabla products.
    Hereda de ProductRepository para reutilizar el mapeo _to_domain.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    def _base_filter(
        self,
        stmt,
        product_type: ProductType,
        category_id: UUID | None,
        search: str | None,
        active_only: bool,
    ):
        stmt = stmt.where(ProductORM.product_type == product_type.value)
        if active_only:
            stmt = stmt.where(ProductORM.is_active == True)  # noqa: E712
        if category_id:
            stmt = stmt.where(ProductORM.category_id == category_id)
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                or_(ProductORM.name.ilike(pattern), ProductORM.sku.ilike(pattern))
            )
        return stmt

    async def _list(
        self,
        product_type: ProductType,
        skip: int,
        limit: int,
        category_id: UUID | None,
        search: str | None,
        active_only: bool,
    ) -> list[Product]:
        stmt = self._base_filter(
            select(ProductORM), product_type, category_id, search, active_only
        )
        stmt = stmt.order_by(ProductORM.name).offset(skip).limit(limit)
        result = await self._session.execute(stmt)
        return [self._to_domain(r) for r in result.scalars().all()]

    async def _count(
        self,
        product_type: ProductType,
        category_id: UUID | None,
        search: str | None,
        active_only: bool,
    ) -> int:
        stmt = self._base_filter(
            select(func.count()).select_from(ProductORM),
            product_type, category_id, search, active_only,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    # ── raw_material ───────────────────────────────────────────────────────
    async def list_raw_materials(
        self,
        skip: int = 0,
        limit: int = 50,
        category_id: UUID | None = None,
        search: str | None = None,
        active_only: bool = True,
    ) -> list[Product]:
        return await self._list(
            ProductType.RAW_MATERIAL, skip, limit, category_id, search, active_only
        )

    async def count_raw_materials(
        self,
        category_id: UUID | None = None,
        search: str | None = None,
        active_only: bool = True,
    ) -> int:
        return await self._count(
            ProductType.RAW_MATERIAL, category_id, search, active_only
        )

    # ── finished_product ───────────────────────────────────────────────────
    async def list_finished_products(
        self,
        skip: int = 0,
        limit: int = 50,
        category_id: UUID | None = None,
        search: str | None = None,
        active_only: bool = True,
    ) -> list[Product]:
        return await self._list(
            ProductType.FINISHED_PRODUCT, skip, limit, category_id, search, active_only
        )

    async def count_finished_products(
        self,
        category_id: UUID | None = None,
        search: str | None = None,
        active_only: bool = True,
    ) -> int:
        return await self._count(
            ProductType.FINISHED_PRODUCT, category_id, search, active_only
        )

    # ── genérico ───────────────────────────────────────────────────────────
    async def list_by_type(
        self,
        product_type: ProductType,
        skip: int = 0,
        limit: int = 50,
        active_only: bool = True,
    ) -> list[Product]:
        return await self._list(product_type, skip, limit, None, None, active_only)

    async def count_by_type(
        self,
        product_type: ProductType,
        active_only: bool = True,
    ) -> int:
        return await self._count(product_type, None, None, active_only)
