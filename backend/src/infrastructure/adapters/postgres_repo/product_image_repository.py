from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.exceptions import NotFoundError
from src.application.ports.repositories.product_image_repository_port import (
    ProductImageRepositoryPort,
)
from src.domain.models.catalog import ProductImage
from src.infrastructure.database.orm_models.product_image_orm import ProductImageORM


class ProductImageRepository(ProductImageRepositoryPort):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_images_for_product(self, product_id: UUID) -> list[ProductImage]:
        stmt = (
            select(ProductImageORM)
            .where(ProductImageORM.product_id == product_id)
            .order_by(ProductImageORM.sort_order.asc())
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(r) for r in result.scalars().all()]

    async def add_image(self, image: ProductImage) -> ProductImage:
        orm = ProductImageORM(
            id=image.id,
            product_id=image.product_id,
            url=image.url,
            alt_text=image.alt_text,
            sort_order=image.sort_order,
            is_primary=image.is_primary,
            created_at=image.created_at,
        )
        self._session.add(orm)
        await self._session.flush()
        return self._to_domain(orm)

    async def set_primary_image(self, product_id: UUID, image_id: UUID) -> None:
        target = await self._session.get(ProductImageORM, image_id)
        if not target or target.product_id != product_id:
            raise NotFoundError("Imagen", str(image_id))

        # 1) Desmarcar todas las del producto (evita violar el índice parcial único)
        await self._session.execute(
            update(ProductImageORM)
            .where(ProductImageORM.product_id == product_id)
            .values(is_primary=False)
        )
        await self._session.flush()

        # 2) Marcar la elegida
        target.is_primary = True
        await self._session.flush()

    async def reorder_images(self, product_id: UUID, ordered_ids: list[UUID]) -> None:
        images = await self.get_images_for_product(product_id)
        existing_ids = {img.id for img in images}
        if existing_ids != set(ordered_ids) or len(ordered_ids) != len(existing_ids):
            raise ValueError(
                "ordered_ids debe contener exactamente los IDs de las imágenes del producto."
            )
        for index, image_id in enumerate(ordered_ids):
            await self._session.execute(
                update(ProductImageORM)
                .where(ProductImageORM.id == image_id)
                .values(sort_order=index)
            )
        await self._session.flush()

    async def delete_image(self, image_id: UUID) -> ProductImage:
        orm = await self._session.get(ProductImageORM, image_id)
        if not orm:
            raise NotFoundError("Imagen", str(image_id))

        deleted = self._to_domain(orm)
        was_primary = orm.is_primary
        product_id = orm.product_id

        await self._session.delete(orm)
        await self._session.flush()

        # Si era la principal y quedan otras, promover la de menor sort_order
        if was_primary:
            remaining = await self.get_images_for_product(product_id)
            if remaining:
                new_primary = min(remaining, key=lambda i: i.sort_order)
                promoted = await self._session.get(ProductImageORM, new_primary.id)
                if promoted:
                    promoted.is_primary = True
                    await self._session.flush()

        return deleted

    @staticmethod
    def _to_domain(orm: ProductImageORM) -> ProductImage:
        return ProductImage(
            id=orm.id,
            product_id=orm.product_id,
            url=orm.url,
            alt_text=orm.alt_text,
            sort_order=orm.sort_order,
            is_primary=orm.is_primary,
            created_at=orm.created_at,
        )
