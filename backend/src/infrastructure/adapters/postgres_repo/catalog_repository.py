from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.application.ports.repositories.catalog_repository_port import CatalogRepositoryPort
from src.domain.models.catalog import CatalogCategory, CatalogProduct, ProductImage
from src.infrastructure.database.orm_models.category_orm import CategoryORM
from src.infrastructure.database.orm_models.product_orm import ProductORM


class CatalogRepository(CatalogRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _base_filter(self):
        """Filtro base: activo y visible en catálogo."""
        return and_(ProductORM.is_active == True, ProductORM.show_in_catalog == True)  # noqa: E712

    def _orm_to_domain(self, orm: ProductORM, category: CategoryORM) -> CatalogProduct:
        images = [
            ProductImage(
                id=img.id,
                product_id=img.product_id,
                url=img.url,
                alt_text=img.alt_text,
                sort_order=img.sort_order,
                is_primary=img.is_primary,
                created_at=img.created_at,
            )
            for img in sorted(orm.images, key=lambda i: (i.sort_order, not i.is_primary))
        ]
        return CatalogProduct(
            id=orm.id,
            sku=orm.sku,
            name=orm.name,
            description=orm.description,
            category_id=orm.category_id,
            category_name=category.name,
            category_slug=category.slug,
            unit=orm.unit,
            attributes=orm.attributes or {},
            images=images,
            is_active=orm.is_active,
            show_in_catalog=orm.show_in_catalog,
            base_price=orm.base_price,
        )

    async def list_catalog_products(
        self,
        category_slug: str | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 24,
    ) -> tuple[list[CatalogProduct], int]:
        stmt = (
            select(ProductORM, CategoryORM)
            .join(CategoryORM, ProductORM.category_id == CategoryORM.id)
            .options(selectinload(ProductORM.images))
            .where(self._base_filter())
        )
        if category_slug:
            stmt = stmt.where(CategoryORM.slug == category_slug)
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                or_(
                    ProductORM.name.ilike(pattern),
                    ProductORM.description.ilike(pattern),
                )
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self._session.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(ProductORM.name.asc()).offset(skip).limit(limit)
        rows = (await self._session.execute(stmt)).all()

        products = [self._orm_to_domain(row.ProductORM, row.CategoryORM) for row in rows]
        return products, total

    async def get_catalog_product_by_sku(self, sku: str) -> CatalogProduct | None:
        stmt = (
            select(ProductORM, CategoryORM)
            .join(CategoryORM, ProductORM.category_id == CategoryORM.id)
            .options(selectinload(ProductORM.images))
            .where(ProductORM.sku == sku)
            .where(self._base_filter())
        )
        row = (await self._session.execute(stmt)).first()
        if row is None:
            return None
        return self._orm_to_domain(row.ProductORM, row.CategoryORM)

    async def list_catalog_categories(self) -> list[CatalogCategory]:
        stmt = (
            select(CategoryORM, func.count(ProductORM.id).label("product_count"))
            .join(
                ProductORM,
                and_(
                    ProductORM.category_id == CategoryORM.id,
                    ProductORM.is_active == True,  # noqa: E712
                    ProductORM.show_in_catalog == True,  # noqa: E712
                ),
                isouter=True,
            )
            .group_by(CategoryORM.id)
            .having(func.count(ProductORM.id) > 0)
            .order_by(CategoryORM.name.asc())
        )
        rows = (await self._session.execute(stmt)).all()
        return [
            CatalogCategory(
                id=row.CategoryORM.id,
                name=row.CategoryORM.name,
                slug=row.CategoryORM.slug,
                description=row.CategoryORM.description,
                product_count=row.product_count,
            )
            for row in rows
        ]

    async def get_related_products(
        self, product_id: UUID, category_id: UUID, limit: int = 4
    ) -> list[CatalogProduct]:
        stmt = (
            select(ProductORM, CategoryORM)
            .join(CategoryORM, ProductORM.category_id == CategoryORM.id)
            .options(selectinload(ProductORM.images))
            .where(self._base_filter())
            .where(ProductORM.category_id == category_id)
            .where(ProductORM.id != product_id)
            .order_by(ProductORM.created_at.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).all()
        return [self._orm_to_domain(row.ProductORM, row.CategoryORM) for row in rows]
