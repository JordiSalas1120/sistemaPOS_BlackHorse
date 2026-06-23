from uuid import UUID

from src.application.dtos.sale_dto import SaleDTO, SaleItemDTO
from src.application.exceptions import NotFoundError
from src.application.ports.repositories.product_repository_port import ProductRepositoryPort
from src.application.ports.repositories.sale_repository_port import SaleRepositoryPort
from src.domain.models.sale import Sale


def _item_to_dto(item, product_sku: str, product_name: str) -> SaleItemDTO:
    return SaleItemDTO(
        id=item.id,
        sale_id=item.sale_id,
        product_id=item.product_id,
        product_sku=product_sku,
        product_name=product_name,
        quantity=item.quantity,
        unit_price=item.unit_price,
        discount_amount=item.discount_amount,
        subtotal=item.subtotal,
    )


def _to_dto(sale: Sale, items_enriched: list[SaleItemDTO]) -> SaleDTO:
    return SaleDTO(
        id=sale.id,
        sale_number=sale.sale_number,
        sale_type=sale.sale_type,
        status=sale.status,
        payment_type=sale.payment_type,
        subtotal=sale.subtotal,
        discount_total=sale.discount_total,
        tax_total=sale.tax_total,
        total=sale.total,
        sold_by=sale.sold_by,
        created_at=sale.created_at,
        updated_at=sale.updated_at,
        items=items_enriched,
        client_id=sale.client_id,
        notes=sale.notes,
    )


class GetSaleUseCase:
    def __init__(self, sale_repo: SaleRepositoryPort, product_repo: ProductRepositoryPort):
        self._sale_repo = sale_repo
        self._product_repo = product_repo

    async def execute(self, sale_id: UUID) -> SaleDTO:
        sale = await self._sale_repo.get_by_id(sale_id)
        if not sale:
            raise NotFoundError("Venta", str(sale_id))

        items_enriched = []
        for item in sale.items:
            product = await self._product_repo.get_by_id(item.product_id)
            items_enriched.append(_item_to_dto(
                item,
                product_sku=product.sku if product else "—",
                product_name=product.name if product else "—",
            ))

        return _to_dto(sale, items_enriched)
