from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.ports.repositories.product_repository_port import ProductRepositoryPort
from src.domain.models.enums import ProductType, ProductUnit
from src.domain.models.product import Product
from src.infrastructure.database.orm_models.product_orm import ProductORM


class ProductRepository(ProductRepositoryPort):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, id: UUID) -> Product | None:
        result = await self._session.get(ProductORM, id)
        return self._to_domain(result) if result else None

    async def get_by_sku(self, sku: str) -> Product | None:
        stmt = select(ProductORM).where(ProductORM.sku == sku)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def list_all(
        self,
        active_only: bool = True,
        category_id: UUID | None = None,
        skip: int = 0,
        limit: int = 50,
        product_type: ProductType | None = None,
    ) -> list[Product]:
        stmt = select(ProductORM)
        if active_only:
            stmt = stmt.where(ProductORM.is_active == True)  # noqa: E712
        if category_id:
            stmt = stmt.where(ProductORM.category_id == category_id)
        if product_type:
            stmt = stmt.where(ProductORM.product_type == product_type.value)
        stmt = stmt.order_by(ProductORM.name).offset(skip).limit(limit)
        result = await self._session.execute(stmt)
        return [self._to_domain(r) for r in result.scalars().all()]

    async def count(
        self,
        active_only: bool = True,
        category_id: UUID | None = None,
        product_type: ProductType | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(ProductORM)
        if active_only:
            stmt = stmt.where(ProductORM.is_active == True)  # noqa: E712
        if category_id:
            stmt = stmt.where(ProductORM.category_id == category_id)
        if product_type:
            stmt = stmt.where(ProductORM.product_type == product_type.value)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def create(self, product: Product) -> Product:
        orm = self._to_orm(product)
        self._session.add(orm)
        await self._session.flush()
        return product

    async def update(self, product: Product) -> Product:
        orm = await self._session.get(ProductORM, product.id)
        if orm:
            orm.name = product.name
            orm.description = product.description
            orm.category_id = product.category_id
            orm.base_price = product.base_price
            orm.wholesale_price = product.wholesale_price
            orm.unit = product.unit
            orm.attributes = product.attributes
            orm.image_url = product.image_url
            orm.is_active = product.is_active
            orm.product_type = product.product_type.value
            orm.show_in_catalog = product.show_in_catalog
            orm.cost_price = product.cost_price
            await self._session.flush()
        return product

    async def delete(self, id: UUID) -> None:
        orm = await self._session.get(ProductORM, id)
        if orm:
            await self._session.delete(orm)
            await self._session.flush()

    @staticmethod
    def _to_domain(orm: ProductORM) -> Product:
        return Product(
            id=orm.id,
            sku=orm.sku,
            name=orm.name,
            description=orm.description,
            category_id=orm.category_id,
            base_price=orm.base_price,
            wholesale_price=orm.wholesale_price,
            unit=ProductUnit(orm.unit),
            attributes=orm.attributes or {},
            image_url=orm.image_url,
            is_active=orm.is_active,
            product_type=ProductType(orm.product_type),
            show_in_catalog=orm.show_in_catalog,
            cost_price=orm.cost_price,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    @staticmethod
    def _to_orm(product: Product) -> ProductORM:
        return ProductORM(
            id=product.id,
            sku=product.sku,
            name=product.name,
            description=product.description,
            category_id=product.category_id,
            base_price=product.base_price,
            wholesale_price=product.wholesale_price,
            unit=product.unit,
            attributes=product.attributes,
            image_url=product.image_url,
            is_active=product.is_active,
            product_type=product.product_type.value,
            show_in_catalog=product.show_in_catalog,
            cost_price=product.cost_price,
        )
