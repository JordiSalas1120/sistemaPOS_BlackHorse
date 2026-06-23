from uuid import UUID

from src.application.dtos.product_dto import ProductDTO, ProductListDTO
from src.application.ports.repositories.category_repository_port import CategoryRepositoryPort
from src.application.ports.repositories.inventory_repository_port import InventoryRepositoryPort
from src.application.ports.repositories.product_repository_port import ProductRepositoryPort
from src.domain.models.enums import ProductType


class ListProductsUseCase:
    def __init__(
        self,
        product_repo: ProductRepositoryPort,
        category_repo: CategoryRepositoryPort,
        inventory_repo: InventoryRepositoryPort,
    ):
        self._product_repo = product_repo
        self._category_repo = category_repo
        self._inventory_repo = inventory_repo

    async def execute(
        self,
        active_only: bool = True,
        category_id: UUID | None = None,
        skip: int = 0,
        limit: int = 50,
        product_type: ProductType | None = None,
    ) -> ProductListDTO:
        products = await self._product_repo.list_all(
            active_only=active_only, category_id=category_id, skip=skip, limit=limit,
            product_type=product_type,
        )
        total = await self._product_repo.count(
            active_only=active_only, category_id=category_id, product_type=product_type
        )

        # Cargar categorías en un solo batch para evitar N+1
        category_ids = {p.category_id for p in products}
        categories = {c.id: c for c in await self._category_repo.list_all() if c.id in category_ids}

        # Cargar inventario en un solo batch
        inventories = {
            inv.product_id: inv
            for inv in await self._inventory_repo.list_all()
            if inv.product_id in {p.id for p in products}
        }

        items = [
            ProductDTO(
                id=p.id,
                sku=p.sku,
                name=p.name,
                description=p.description,
                category_id=p.category_id,
                category_name=categories[p.category_id].name if p.category_id in categories else "—",
                base_price=p.base_price,
                wholesale_price=p.wholesale_price,
                unit=p.unit,
                attributes=p.attributes,
                image_url=p.image_url,
                is_active=p.is_active,
                quantity_on_hand=inventories[p.id].quantity_on_hand if p.id in inventories else None,
                product_type=p.product_type,
                show_in_catalog=p.show_in_catalog,
                cost_price=p.cost_price,
            )
            for p in products
        ]

        return ProductListDTO(items=items, total=total, skip=skip, limit=limit)
