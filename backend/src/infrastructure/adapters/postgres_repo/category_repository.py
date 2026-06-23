from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.ports.repositories.category_repository_port import CategoryRepositoryPort
from src.domain.models.product import Category
from src.infrastructure.database.orm_models.category_orm import CategoryORM


class CategoryRepository(CategoryRepositoryPort):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, id: UUID) -> Category | None:
        result = await self._session.get(CategoryORM, id)
        return self._to_domain(result) if result else None

    async def get_by_slug(self, slug: str) -> Category | None:
        stmt = select(CategoryORM).where(CategoryORM.slug == slug)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def list_all(self) -> list[Category]:
        stmt = select(CategoryORM).order_by(CategoryORM.name)
        result = await self._session.execute(stmt)
        return [self._to_domain(r) for r in result.scalars().all()]

    async def create(self, category: Category) -> Category:
        orm = self._to_orm(category)
        self._session.add(orm)
        await self._session.flush()
        return category

    async def update(self, category: Category) -> Category:
        orm = await self._session.get(CategoryORM, category.id)
        if orm:
            orm.name = category.name
            orm.slug = category.slug
            orm.description = category.description
            await self._session.flush()
        return category

    @staticmethod
    def _to_domain(orm: CategoryORM) -> Category:
        return Category(
            id=orm.id,
            name=orm.name,
            slug=orm.slug,
            description=orm.description,
            created_at=orm.created_at,
        )

    @staticmethod
    def _to_orm(category: Category) -> CategoryORM:
        return CategoryORM(
            id=category.id,
            name=category.name,
            slug=category.slug,
            description=category.description,
        )
