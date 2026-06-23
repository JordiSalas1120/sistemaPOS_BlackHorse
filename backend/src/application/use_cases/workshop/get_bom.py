import uuid

from src.application.dtos.bom_dto import BOMWithCostDTO
from src.application.exceptions import NotFoundError
from src.application.ports.repositories.bom_repository_port import BOMRepositoryPort
from src.application.ports.repositories.product_repository_port import ProductRepositoryPort


class GetBOMUseCase:
    def __init__(
        self,
        bom_repo: BOMRepositoryPort,
        product_repo: ProductRepositoryPort,
    ):
        self._bom_repo = bom_repo
        self._product_repo = product_repo

    async def execute(self, product_id: uuid.UUID) -> BOMWithCostDTO:
        bom = await self._bom_repo.get_bom_by_product_id(product_id)
        if not bom:
            raise NotFoundError("BOM", f"producto {product_id}")

        bom, items = await self._bom_repo.get_bom_with_items(bom.id)

        # Construir mapa de precios: usa cost_price si existe, si no base_price
        prices = {}
        material_names = {}
        for item in items:
            material = await self._product_repo.get_by_id(item.material_id)
            if material:
                prices[item.material_id] = material.cost_price or material.base_price
                material_names[item.material_id] = material.name

        bom.items = items
        total_cost = bom.calculate_material_cost(prices) if prices else None
        cost_per_unit = bom.cost_per_unit(prices) if prices else None

        return BOMWithCostDTO.from_domain(
            bom=bom,
            items=items,
            total_cost=total_cost,
            cost_per_unit=cost_per_unit,
            material_names=material_names,
        )
