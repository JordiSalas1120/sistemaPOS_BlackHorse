from uuid import UUID

from src.application.dtos.workshop_dto import WorkshopProductDTO, WorkshopProductListDTO
from src.application.ports.repositories.workshop_product_repository_port import (
    WorkshopProductRepositoryPort,
)
from src.domain.models.enums import ProductType


class ListWorkshopProductsUseCase:
    def __init__(self, workshop_repo: WorkshopProductRepositoryPort):
        self._repo = workshop_repo

    async def execute(
        self,
        product_type: ProductType,
        skip: int = 0,
        limit: int = 50,
        category_id: UUID | None = None,
        search: str | None = None,
        active_only: bool = True,
    ) -> WorkshopProductListDTO:
        if product_type == ProductType.RAW_MATERIAL:
            items = await self._repo.list_raw_materials(
                skip=skip, limit=limit, category_id=category_id,
                search=search, active_only=active_only,
            )
            total = await self._repo.count_raw_materials(
                category_id=category_id, search=search, active_only=active_only,
            )
        elif product_type == ProductType.FINISHED_PRODUCT:
            items = await self._repo.list_finished_products(
                skip=skip, limit=limit, category_id=category_id,
                search=search, active_only=active_only,
            )
            total = await self._repo.count_finished_products(
                category_id=category_id, search=search, active_only=active_only,
            )
        else:
            items = await self._repo.list_by_type(
                product_type=product_type, skip=skip, limit=limit, active_only=active_only,
            )
            total = await self._repo.count_by_type(
                product_type=product_type, active_only=active_only,
            )

        return WorkshopProductListDTO(
            items=[WorkshopProductDTO.from_product(p) for p in items],
            total=total,
            skip=skip,
            limit=limit,
            product_type=product_type,
        )
