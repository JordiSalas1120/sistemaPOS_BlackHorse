import uuid
from decimal import Decimal

from src.application.dtos.bom_dto import BOMCostDetailDTO, BOMCostLineDTO
from src.application.exceptions import NotFoundError
from src.application.ports.repositories.bom_repository_port import BOMRepositoryPort
from src.application.ports.repositories.product_repository_port import ProductRepositoryPort


class CalculateBOMCostUseCase:
    """
    Calcula el costo detallado de una BOM usando precios actuales de los materiales.
    Retorna un desglose línea por línea con subtotales.
    """

    def __init__(self, bom_repo: BOMRepositoryPort, product_repo: ProductRepositoryPort):
        self._bom_repo = bom_repo
        self._product_repo = product_repo

    async def execute(self, product_id: uuid.UUID) -> BOMCostDetailDTO:
        bom = await self._bom_repo.get_bom_by_product_id(product_id)
        if not bom:
            raise NotFoundError("BOM", f"producto {product_id}")

        _, items = await self._bom_repo.get_bom_with_items(bom.id)

        lines: list[BOMCostLineDTO] = []
        total = Decimal("0")

        for item in items:
            material = await self._product_repo.get_by_id(item.material_id)
            if not material:
                raise NotFoundError("Material", str(item.material_id))

            unit_price = material.cost_price or material.base_price
            effective_qty = item.effective_quantity
            subtotal = effective_qty * unit_price
            total += subtotal

            lines.append(BOMCostLineDTO(
                material_id=item.material_id,
                material_name=material.name,
                material_sku=material.sku,
                unit=material.unit,
                quantity_required=item.quantity_required,
                scrap_factor=item.scrap_factor,
                effective_quantity=effective_qty,
                unit_price=unit_price,
                subtotal=subtotal,
            ))

        cost_per_unit = total / bom.output_quantity if bom.output_quantity else Decimal("0")

        return BOMCostDetailDTO(
            bom_id=bom.id,
            finished_product_id=product_id,
            output_quantity=bom.output_quantity,
            lines=lines,
            total_material_cost=total,
            cost_per_unit=cost_per_unit,
            labor_minutes=bom.labor_minutes,
        )
