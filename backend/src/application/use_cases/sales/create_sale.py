import uuid
from datetime import datetime, timezone

from src.application.dtos.inventory_dto import AdjustStockDTO
from src.application.dtos.sale_dto import CreateSaleDTO, SaleDTO, SaleItemDTO
from src.application.exceptions import BusinessRuleViolation, NotFoundError
from src.application.ports.repositories.audit_log_repository_port import AuditLogRepositoryPort
from src.application.ports.repositories.category_repository_port import CategoryRepositoryPort
from src.application.ports.repositories.client_repository_port import ClientRepositoryPort
from src.application.ports.repositories.inventory_repository_port import InventoryRepositoryPort
from src.application.ports.repositories.price_rule_repository_port import PriceRuleRepositoryPort
from src.application.ports.repositories.product_repository_port import ProductRepositoryPort
from src.application.ports.repositories.sale_repository_port import SaleRepositoryPort
from src.application.use_cases.inventory.adjust_stock import AdjustStockUseCase
from src.application.use_cases.sales.get_sale import _item_to_dto, _to_dto
from src.domain.models.audit_log import AuditLog
from src.domain.models.client import Client
from src.domain.models.enums import AuditAction, ClientType, MovementType
from src.domain.models.sale import Sale, SaleItem
from src.domain.services.crm_tagging_service import CrmTaggingService
from src.domain.services.inventory_service import InventoryService
from src.domain.services.pricing_service import PricingService


class CreateSaleUseCase:
    def __init__(
        self,
        sale_repo: SaleRepositoryPort,
        product_repo: ProductRepositoryPort,
        inventory_repo: InventoryRepositoryPort,
        client_repo: ClientRepositoryPort,
        category_repo: CategoryRepositoryPort,
        price_rule_repo: PriceRuleRepositoryPort,
        audit_repo: AuditLogRepositoryPort,
        pricing_service: PricingService,
        inventory_service: InventoryService,
        crm_tagging_service: CrmTaggingService,
    ):
        self._sale_repo = sale_repo
        self._product_repo = product_repo
        self._inventory_repo = inventory_repo
        self._client_repo = client_repo
        self._category_repo = category_repo
        self._price_rule_repo = price_rule_repo
        self._audit_repo = audit_repo
        self._pricing_service = pricing_service
        self._inventory_service = inventory_service
        self._crm_tagging_service = crm_tagging_service

    async def execute(self, dto: CreateSaleDTO, actor: str = "system") -> SaleDTO:
        if not dto.items:
            raise BusinessRuleViolation("La venta debe tener al menos un ítem.")

        # Resolver cliente
        client: Client | None = None
        if dto.client_id:
            client = await self._client_repo.get_by_id(dto.client_id)
            if not client:
                raise NotFoundError("Cliente", str(dto.client_id))

        # Cargar reglas de precios activas
        price_rules = await self._price_rule_repo.list_active()
        client_type = client.client_type if client else ClientType.RETAIL

        now = datetime.now(timezone.utc)
        sale_items: list[SaleItem] = []
        sale_items_enriched: list[SaleItemDTO] = []
        sold_category_ids: set = set()

        for item_input in dto.items:
            product = await self._product_repo.get_by_id(item_input.product_id)
            if not product:
                raise NotFoundError("Producto", str(item_input.product_id))
            if not product.is_active:
                raise BusinessRuleViolation(f"El producto '{product.name}' no está activo.")

            inventory = await self._inventory_repo.get_by_product_id(item_input.product_id)
            if not inventory:
                raise NotFoundError("Inventario", str(item_input.product_id))
            if not self._inventory_service.can_fulfill_order(inventory, item_input.quantity):
                raise BusinessRuleViolation(
                    f"Stock insuficiente para '{product.name}': "
                    f"disponible {inventory.quantity_on_hand}, solicitado {item_input.quantity}"
                )

            unit_price, discount_per_unit = self._pricing_service.calculate_unit_price(
                base_price=product.base_price,
                quantity=item_input.quantity,
                client_type=client_type,
                product_id=product.id,
                category_id=product.category_id,
                rules=price_rules,
                now=now,
            )

            sale_item = SaleItem(
                id=uuid.uuid4(),
                sale_id=uuid.uuid4(),  # placeholder
                product_id=product.id,
                quantity=item_input.quantity,
                unit_price=unit_price,
                discount_amount=discount_per_unit * item_input.quantity,
            )
            sale_items.append(sale_item)
            sale_items_enriched.append(_item_to_dto(sale_item, product.sku, product.name))
            sold_category_ids.add(product.category_id)

        # Calcular totales
        totals = self._pricing_service.calculate_cart_totals([
            {
                "unit_price": i.unit_price,
                "quantity": i.quantity,
                "discount_amount": (i.discount_amount / i.quantity) if i.quantity else i.discount_amount,
            }
            for i in sale_items
        ])

        # Generar número de venta y armar Sale
        sale_number = await self._sale_repo.next_sale_number(now.year)
        sale_id = uuid.uuid4()
        for item in sale_items:
            item.sale_id = sale_id

        sale = Sale(
            id=sale_id,
            sale_number=sale_number,
            sale_type=dto.sale_type,
            status="completed",
            payment_type=dto.payment_type,
            subtotal=totals["subtotal"],
            discount_total=totals["discount_total"],
            tax_total=totals["tax_total"],
            total=totals["total"],
            sold_by=actor,
            created_at=now,
            updated_at=now,
            items=sale_items,
            client_id=dto.client_id,
            notes=dto.notes,
        )
        saved_sale = await self._sale_repo.create(sale)

        # Descontar stock
        for item in sale_items:
            adjust_uc = AdjustStockUseCase(
                self._inventory_repo, self._product_repo, self._audit_repo, self._inventory_service
            )
            await adjust_uc.execute(AdjustStockDTO(
                product_id=item.product_id,
                quantity_delta=-item.quantity,
                movement_type=MovementType.SALE,
                actor=actor,
                reference_id=sale_id,
                notes=f"Venta {sale_number}",
            ))

        # CRM tagging si hay cliente
        if client:
            categories = await self._category_repo.list_all()
            sold_slugs = [c.slug for c in categories if c.id in sold_category_ids]
            added_tags = self._crm_tagging_service.apply_post_sale_tags(client, saved_sale, sold_slugs)
            if added_tags:
                await self._client_repo.update(client)

        # Auditoría
        await self._audit_repo.create(AuditLog(
            id=uuid.uuid4(),
            entity_type="sale",
            entity_id=sale_id,
            action=AuditAction.SALE,
            actor=actor,
            payload={
                "sale_number": sale_number,
                "total": str(totals["total"]),
                "items_count": len(sale_items),
                "client_id": str(dto.client_id) if dto.client_id else None,
            },
            created_at=now,
        ))

        return _to_dto(saved_sale, sale_items_enriched)
