from datetime import datetime
from uuid import UUID

from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.ports.repositories.production_order_repository_port import (
    ProductionOrderRepositoryPort,
)
from src.domain.models.enums import ProductionOrderStatus
from src.domain.models.production_order import ProductionOrder, ProductionOrderItem
from src.infrastructure.database.orm_models.production_order_orm import (
    ProductionOrderItemORM,
    ProductionOrderORM,
)


class ProductionOrderRepository(ProductionOrderRepositoryPort):
    def __init__(self, session: AsyncSession):
        self._session = session

    # ── next_order_number ── mismo patrón que SaleRepository ─────────────────

    async def next_order_number(self, year: int) -> str:
        stmt = select(func.count()).select_from(ProductionOrderORM).where(
            extract("year", ProductionOrderORM.created_at) == year
        )
        result = await self._session.execute(stmt)
        count = result.scalar_one()
        return f"ORD-{year}-{count + 1:05d}"

    # ── create_order ──────────────────────────────────────────────────────────

    async def create_order(
        self,
        order: ProductionOrder,
        items: list[ProductionOrderItem],
    ) -> ProductionOrder:
        orm = ProductionOrderORM(
            id=order.id,
            order_number=order.order_number,
            bom_id=order.bom_id,
            finished_product_id=order.finished_product_id,
            quantity_to_produce=order.quantity_to_produce,
            quantity_produced=order.quantity_produced,
            status=order.status,
            produced_by=order.produced_by,
            notes=order.notes,
            created_at=order.created_at,
            updated_at=order.updated_at,
        )
        self._session.add(orm)
        await self._session.flush()

        for item in items:
            item_orm = ProductionOrderItemORM(
                id=item.id,
                order_id=order.id,
                material_id=item.material_id,
                quantity_required=item.quantity_required,
                quantity_consumed=item.quantity_consumed,
                unit_cost_snapshot=item.unit_cost_snapshot,
                notes=item.notes,
            )
            self._session.add(item_orm)

        await self._session.flush()
        return order

    # ── get_order ─────────────────────────────────────────────────────────────

    async def get_order(self, order_id: UUID) -> ProductionOrder | None:
        stmt = select(ProductionOrderORM).where(ProductionOrderORM.id == order_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def get_order_with_items(
        self, order_id: UUID
    ) -> tuple[ProductionOrder, list[ProductionOrderItem]] | None:
        order = await self.get_order(order_id)
        if not order:
            return None
        items = await self.get_order_items(order_id)
        return order, items

    # ── get_order_items ───────────────────────────────────────────────────────

    async def get_order_items(self, order_id: UUID) -> list[ProductionOrderItem]:
        stmt = select(ProductionOrderItemORM).where(
            ProductionOrderItemORM.order_id == order_id
        )
        result = await self._session.execute(stmt)
        return [self._to_item_domain(r) for r in result.scalars().all()]

    # ── list_orders ───────────────────────────────────────────────────────────

    async def list_orders(
        self,
        status: ProductionOrderStatus | None = None,
        finished_product_id: UUID | None = None,
        produced_by: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[ProductionOrder], int]:
        base_stmt = select(ProductionOrderORM)

        if status:
            base_stmt = base_stmt.where(ProductionOrderORM.status == status.value)
        if finished_product_id:
            base_stmt = base_stmt.where(
                ProductionOrderORM.finished_product_id == finished_product_id
            )
        if produced_by:
            base_stmt = base_stmt.where(ProductionOrderORM.produced_by == produced_by)
        if date_from:
            base_stmt = base_stmt.where(ProductionOrderORM.created_at >= date_from)
        if date_to:
            base_stmt = base_stmt.where(ProductionOrderORM.created_at <= date_to)

        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar_one()

        paginated = (
            base_stmt.order_by(ProductionOrderORM.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self._session.execute(paginated)
        orders = [self._to_domain(r) for r in result.scalars().all()]
        return orders, total

    # ── update_order ──────────────────────────────────────────────────────────

    async def update_order(self, order: ProductionOrder) -> ProductionOrder:
        orm = await self._session.get(ProductionOrderORM, order.id)
        if not orm:
            return order
        orm.status = order.status
        orm.quantity_produced = order.quantity_produced
        orm.unit_cost_snapshot = order.unit_cost_snapshot
        orm.started_at = order.started_at
        orm.completed_at = order.completed_at
        orm.cancelled_at = order.cancelled_at
        orm.notes = order.notes
        orm.updated_at = order.updated_at
        await self._session.flush()
        return order

    # ── update_order_items ────────────────────────────────────────────────────

    async def update_order_items(
        self, items: list[ProductionOrderItem]
    ) -> list[ProductionOrderItem]:
        for item in items:
            orm = await self._session.get(ProductionOrderItemORM, item.id)
            if orm:
                orm.quantity_consumed = item.quantity_consumed
                orm.notes = item.notes
        await self._session.flush()
        return items

    # ── mappers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _to_domain(orm: ProductionOrderORM) -> ProductionOrder:
        return ProductionOrder(
            id=orm.id,
            order_number=orm.order_number,
            bom_id=orm.bom_id,
            finished_product_id=orm.finished_product_id,
            quantity_to_produce=orm.quantity_to_produce,
            quantity_produced=orm.quantity_produced,
            status=ProductionOrderStatus(orm.status),
            produced_by=orm.produced_by,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            unit_cost_snapshot=orm.unit_cost_snapshot,
            started_at=orm.started_at,
            completed_at=orm.completed_at,
            cancelled_at=orm.cancelled_at,
            notes=orm.notes,
        )

    @staticmethod
    def _to_item_domain(orm: ProductionOrderItemORM) -> ProductionOrderItem:
        return ProductionOrderItem(
            id=orm.id,
            order_id=orm.order_id,
            material_id=orm.material_id,
            quantity_required=orm.quantity_required,
            quantity_consumed=orm.quantity_consumed,
            unit_cost_snapshot=orm.unit_cost_snapshot,
            notes=orm.notes,
        )
