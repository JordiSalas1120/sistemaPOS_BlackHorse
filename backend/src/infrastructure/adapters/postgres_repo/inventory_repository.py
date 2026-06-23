from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.ports.repositories.inventory_repository_port import InventoryRepositoryPort
from src.domain.models.enums import MovementType
from src.domain.models.inventory import Inventory, InventoryMovement
from src.infrastructure.database.orm_models.inventory_orm import InventoryMovementORM, InventoryORM


class InventoryRepository(InventoryRepositoryPort):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_product_id(self, product_id: UUID) -> Inventory | None:
        stmt = select(InventoryORM).where(InventoryORM.product_id == product_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def list_all(self) -> list[Inventory]:
        stmt = select(InventoryORM)
        result = await self._session.execute(stmt)
        return [self._to_domain(r) for r in result.scalars().all()]

    async def list_low_stock(self) -> list[Inventory]:
        stmt = select(InventoryORM).where(
            InventoryORM.quantity_on_hand <= InventoryORM.low_stock_threshold
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(r) for r in result.scalars().all()]

    async def create(self, inventory: Inventory) -> Inventory:
        orm = InventoryORM(
            id=inventory.id,
            product_id=inventory.product_id,
            quantity_on_hand=inventory.quantity_on_hand,
            low_stock_threshold=inventory.low_stock_threshold,
        )
        self._session.add(orm)
        await self._session.flush()
        return inventory

    async def update(self, inventory: Inventory) -> Inventory:
        orm = await self._session.get(InventoryORM, inventory.id)
        if orm:
            orm.quantity_on_hand = inventory.quantity_on_hand
            orm.low_stock_threshold = inventory.low_stock_threshold
            orm.last_restocked_at = inventory.last_restocked_at
            await self._session.flush()
        return inventory

    async def create_movement(self, movement: InventoryMovement) -> InventoryMovement:
        orm = InventoryMovementORM(
            id=movement.id,
            product_id=movement.product_id,
            movement_type=movement.movement_type,
            quantity_delta=movement.quantity_delta,
            quantity_before=movement.quantity_before,
            quantity_after=movement.quantity_after,
            reference_id=movement.reference_id,
            notes=movement.notes,
            created_by=movement.created_by,
        )
        self._session.add(orm)
        await self._session.flush()
        return movement

    async def list_movements(
        self, product_id: UUID, skip: int = 0, limit: int = 50
    ) -> list[InventoryMovement]:
        stmt = (
            select(InventoryMovementORM)
            .where(InventoryMovementORM.product_id == product_id)
            .order_by(InventoryMovementORM.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_movement_domain(r) for r in result.scalars().all()]

    @staticmethod
    def _to_domain(orm: InventoryORM) -> Inventory:
        return Inventory(
            id=orm.id,
            product_id=orm.product_id,
            quantity_on_hand=orm.quantity_on_hand,
            low_stock_threshold=orm.low_stock_threshold,
            last_restocked_at=orm.last_restocked_at,
            updated_at=orm.updated_at,
        )

    @staticmethod
    def _to_movement_domain(orm: InventoryMovementORM) -> InventoryMovement:
        return InventoryMovement(
            id=orm.id,
            product_id=orm.product_id,
            movement_type=MovementType(orm.movement_type),
            quantity_delta=orm.quantity_delta,
            quantity_before=orm.quantity_before,
            quantity_after=orm.quantity_after,
            reference_id=orm.reference_id,
            notes=orm.notes,
            created_by=orm.created_by,
            created_at=orm.created_at,
        )
