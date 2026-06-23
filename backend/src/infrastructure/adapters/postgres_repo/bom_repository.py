from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.application.exceptions import AlreadyExistsError, NotFoundError
from src.application.ports.repositories.bom_repository_port import BOMRepositoryPort
from src.domain.models.bom import BOM, BOMItem
from src.infrastructure.database.orm_models.bom_orm import BomItemORM, BomORM


class BOMRepository(BOMRepositoryPort):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_bom_by_product_id(self, product_id: UUID) -> BOM | None:
        stmt = select(BomORM).where(BomORM.finished_product_id == product_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def create_bom(self, bom: BOM) -> BOM:
        orm = BomORM(
            id=bom.id,
            finished_product_id=bom.finished_product_id,
            output_quantity=bom.output_quantity,
            labor_minutes=bom.labor_minutes,
            notes=bom.notes,
            is_active=bom.is_active,
        )
        orm.items = [
            BomItemORM(
                id=item.id,
                bom_id=bom.id,
                material_id=item.material_id,
                quantity_required=item.quantity_required,
                scrap_factor=item.scrap_factor,
                notes=item.notes,
                sort_order=item.sort_order,
            )
            for item in bom.items
        ]
        self._session.add(orm)
        await self._session.flush()
        return bom

    async def update_bom(self, bom: BOM) -> BOM:
        orm = await self._session.get(BomORM, bom.id)
        if not orm:
            raise NotFoundError("BOM", str(bom.id))
        orm.output_quantity = bom.output_quantity
        orm.labor_minutes = bom.labor_minutes
        orm.notes = bom.notes
        orm.is_active = bom.is_active
        await self._session.flush()
        return bom

    async def delete_bom(self, bom_id: UUID) -> None:
        orm = await self._session.get(BomORM, bom_id)
        if not orm:
            raise NotFoundError("BOM", str(bom_id))
        await self._session.delete(orm)
        await self._session.flush()

    async def get_bom_with_items(self, bom_id: UUID) -> tuple[BOM, list[BOMItem]]:
        stmt = (
            select(BomORM)
            .where(BomORM.id == bom_id)
            .options(selectinload(BomORM.items))
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if not orm:
            raise NotFoundError("BOM", str(bom_id))
        items = [self._item_to_domain(i) for i in orm.items]
        bom = self._to_domain(orm)
        bom.items = items
        return bom, items

    async def add_bom_item(self, item: BOMItem) -> BOMItem:
        orm = BomItemORM(
            id=item.id,
            bom_id=item.bom_id,
            material_id=item.material_id,
            quantity_required=item.quantity_required,
            scrap_factor=item.scrap_factor,
            notes=item.notes,
            sort_order=item.sort_order,
        )
        self._session.add(orm)
        try:
            await self._session.flush()
        except IntegrityError:
            await self._session.rollback()
            raise AlreadyExistsError("BOMItem", "material_id", str(item.material_id))
        return item

    async def remove_bom_item(self, bom_item_id: UUID) -> None:
        orm = await self._session.get(BomItemORM, bom_item_id)
        if not orm:
            raise NotFoundError("BOMItem", str(bom_item_id))
        await self._session.delete(orm)
        await self._session.flush()

    async def update_bom_item(self, item: BOMItem) -> BOMItem:
        orm = await self._session.get(BomItemORM, item.id)
        if not orm:
            raise NotFoundError("BOMItem", str(item.id))
        orm.quantity_required = item.quantity_required
        orm.scrap_factor = item.scrap_factor
        orm.notes = item.notes
        orm.sort_order = item.sort_order
        await self._session.flush()
        return item

    @staticmethod
    def _to_domain(orm: BomORM) -> BOM:
        return BOM(
            id=orm.id,
            finished_product_id=orm.finished_product_id,
            output_quantity=orm.output_quantity,
            is_active=orm.is_active,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            labor_minutes=orm.labor_minutes,
            notes=orm.notes,
            items=[],
        )

    @staticmethod
    def _item_to_domain(orm: BomItemORM) -> BOMItem:
        return BOMItem(
            id=orm.id,
            bom_id=orm.bom_id,
            material_id=orm.material_id,
            quantity_required=orm.quantity_required,
            scrap_factor=orm.scrap_factor,
            notes=orm.notes,
            sort_order=orm.sort_order,
        )
