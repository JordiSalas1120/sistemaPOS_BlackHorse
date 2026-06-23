from datetime import datetime
from uuid import UUID

from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.application.ports.repositories.sale_repository_port import SaleRepositoryPort
from src.domain.models.enums import PaymentType, SaleStatus, SaleType
from src.domain.models.sale import Sale, SaleItem
from src.infrastructure.database.orm_models.sale_orm import SaleItemORM, SaleORM


class SaleRepository(SaleRepositoryPort):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, id: UUID) -> Sale | None:
        stmt = (
            select(SaleORM)
            .options(selectinload(SaleORM.items))
            .where(SaleORM.id == id)
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def get_by_sale_number(self, sale_number: str) -> Sale | None:
        stmt = (
            select(SaleORM)
            .options(selectinload(SaleORM.items))
            .where(SaleORM.sale_number == sale_number)
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def list_all(
        self,
        client_id: UUID | None = None,
        status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Sale]:
        stmt = select(SaleORM).options(selectinload(SaleORM.items))
        if client_id:
            stmt = stmt.where(SaleORM.client_id == client_id)
        if status:
            stmt = stmt.where(SaleORM.status == status)
        if date_from:
            stmt = stmt.where(SaleORM.created_at >= date_from)
        if date_to:
            stmt = stmt.where(SaleORM.created_at <= date_to)
        stmt = stmt.order_by(SaleORM.created_at.desc()).offset(skip).limit(limit)
        result = await self._session.execute(stmt)
        return [self._to_domain(r) for r in result.scalars().all()]

    async def count(
        self,
        client_id: UUID | None = None,
        status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(SaleORM)
        if client_id:
            stmt = stmt.where(SaleORM.client_id == client_id)
        if status:
            stmt = stmt.where(SaleORM.status == status)
        if date_from:
            stmt = stmt.where(SaleORM.created_at >= date_from)
        if date_to:
            stmt = stmt.where(SaleORM.created_at <= date_to)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def next_sale_number(self, year: int) -> str:
        """Genera el próximo número con formato VTA-YYYY-NNNNN."""
        stmt = select(func.count()).select_from(SaleORM).where(
            extract("year", SaleORM.created_at) == year
        )
        result = await self._session.execute(stmt)
        count = result.scalar_one()
        return f"VTA-{year}-{count + 1:05d}"

    async def create(self, sale: Sale) -> Sale:
        orm = SaleORM(
            id=sale.id,
            sale_number=sale.sale_number,
            client_id=sale.client_id,
            sale_type=sale.sale_type,
            status=sale.status,
            payment_type=sale.payment_type,
            subtotal=sale.subtotal,
            discount_total=sale.discount_total,
            tax_total=sale.tax_total,
            total=sale.total,
            notes=sale.notes,
            sold_by=sale.sold_by,
        )
        self._session.add(orm)
        await self._session.flush()

        for item in sale.items:
            self._session.add(SaleItemORM(
                id=item.id,
                sale_id=sale.id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                discount_amount=item.discount_amount,
            ))
        await self._session.flush()
        return sale

    async def update(self, sale: Sale) -> Sale:
        orm = await self._session.get(SaleORM, sale.id)
        if orm:
            orm.status = sale.status
            orm.notes = sale.notes
            await self._session.flush()
        return sale

    @staticmethod
    def _to_domain(orm: SaleORM) -> Sale:
        items = [
            SaleItem(
                id=i.id,
                sale_id=i.sale_id,
                product_id=i.product_id,
                quantity=i.quantity,
                unit_price=i.unit_price,
                discount_amount=i.discount_amount,
            )
            for i in (orm.items or [])
        ]
        return Sale(
            id=orm.id,
            sale_number=orm.sale_number,
            sale_type=SaleType(orm.sale_type),
            status=SaleStatus(orm.status),
            payment_type=PaymentType(orm.payment_type),
            subtotal=orm.subtotal,
            discount_total=orm.discount_total,
            tax_total=orm.tax_total,
            total=orm.total,
            sold_by=orm.sold_by,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            items=items,
            client_id=orm.client_id,
            notes=orm.notes,
        )
