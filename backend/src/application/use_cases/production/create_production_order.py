import uuid
from datetime import datetime, timezone
from decimal import Decimal

from src.application.dtos.production_dto import (
    CreateProductionOrderDTO,
    ProductionOrderDTO,
    _to_dto,
)
from src.application.exceptions import BusinessRuleViolation, NotFoundError
from src.application.ports.repositories.bom_repository_port import BOMRepositoryPort
from src.application.ports.repositories.product_repository_port import ProductRepositoryPort
from src.application.ports.repositories.production_order_repository_port import (
    ProductionOrderRepositoryPort,
)
from src.domain.models.enums import ProductionOrderStatus
from src.domain.models.production_order import ProductionOrder, ProductionOrderItem


class CreateProductionOrderUseCase:
    """
    Crea una orden de producción en estado DRAFT con snapshot de ítems y precios.
    No descuenta stock. No valida disponibilidad (eso es responsabilidad de StartProductionOrder).
    """

    def __init__(
        self,
        order_repo: ProductionOrderRepositoryPort,
        product_repo: ProductRepositoryPort,
        bom_repo: BOMRepositoryPort,
    ):
        self._order_repo = order_repo
        self._product_repo = product_repo
        self._bom_repo = bom_repo

    async def execute(self, dto: CreateProductionOrderDTO) -> ProductionOrderDTO:
        # 1. Validar BOM (get_bom_with_items lanza NotFoundError si no existe)
        bom, bom_items = await self._bom_repo.get_bom_with_items(dto.bom_id)
        if not bom.is_active:
            raise BusinessRuleViolation(
                f"El BOM '{bom.id}' no está activo y no puede usarse para producir."
            )
        if not bom_items:
            raise BusinessRuleViolation(
                "El BOM no tiene ítems de materiales. No se puede crear una orden de producción."
            )

        # 2. Validar producto terminado
        finished_product = await self._product_repo.get_by_id(bom.finished_product_id)
        if not finished_product:
            raise NotFoundError("Producto terminado", str(bom.finished_product_id))
        if not finished_product.is_active:
            raise BusinessRuleViolation(
                f"El producto terminado '{finished_product.name}' no está activo."
            )

        # 3. Construir snapshot de ítems con precios actuales
        now = datetime.now(timezone.utc)
        order_id = uuid.uuid4()
        order_items: list[ProductionOrderItem] = []
        material_info: dict = {}

        for bom_item in bom_items:
            material = await self._product_repo.get_by_id(bom_item.material_id)
            if not material:
                raise NotFoundError("Material", str(bom_item.material_id))
            if not material.is_active:
                raise BusinessRuleViolation(
                    f"El material '{material.name}' (SKU: {material.sku}) no está activo."
                )

            material_info[bom_item.material_id] = (material.sku, material.name)
            order_items.append(
                ProductionOrderItem(
                    id=uuid.uuid4(),
                    order_id=order_id,
                    material_id=bom_item.material_id,
                    # cantidad neta por unidad de producto terminado (sin scrap — fuera de alcance S2)
                    quantity_required=bom_item.quantity_required,
                    # costo de compra del insumo (cae a base_price si no hay cost_price)
                    unit_cost_snapshot=material.cost_price or material.base_price,
                    quantity_consumed=Decimal("0"),
                )
            )

        # 4. Generar número de orden
        order_number = await self._order_repo.next_order_number(now.year)

        # 5. Construir la orden
        order = ProductionOrder(
            id=order_id,
            order_number=order_number,
            bom_id=dto.bom_id,
            finished_product_id=bom.finished_product_id,
            quantity_to_produce=dto.quantity_to_produce,
            produced_by=dto.produced_by,
            status=ProductionOrderStatus.DRAFT,
            created_at=now,
            updated_at=now,
            notes=dto.notes,
        )

        # 6. Persistir (no descuenta stock)
        saved_order = await self._order_repo.create_order(order, order_items)
        saved_items = await self._order_repo.get_order_items(order_id)

        return _to_dto(
            saved_order,
            saved_items,
            material_info=material_info,
            finished_product_name=finished_product.name,
            finished_product_sku=finished_product.sku,
        )
