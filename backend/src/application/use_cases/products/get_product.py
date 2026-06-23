from uuid import UUID

from src.application.dtos.product_dto import ProductDTO
from src.application.exceptions import NotFoundError
from src.application.ports.repositories.category_repository_port import CategoryRepositoryPort
from src.application.ports.repositories.inventory_repository_port import InventoryRepositoryPort
from src.application.ports.repositories.product_repository_port import ProductRepositoryPort


class GetProductUseCase:
    def __init__(
        self,
        product_repo: ProductRepositoryPort,
        category_repo: CategoryRepositoryPort,
        inventory_repo: InventoryRepositoryPort,
    ):
        self._product_repo = product_repo
        self._category_repo = category_repo
        self._inventory_repo = inventory_repo

    async def execute(self, product_id: UUID) -> ProductDTO:
        product = await self._product_repo.get_by_id(product_id)
        if not product:
            raise NotFoundError("Producto", str(product_id))

        category = await self._category_repo.get_by_id(product.category_id)
        inventory = await self._inventory_repo.get_by_product_id(product_id)

        return ProductDTO(
            id=product.id,
            sku=product.sku,
            name=product.name,
            description=product.description,
            category_id=product.category_id,
            category_name=category.name if category else "—",
            base_price=product.base_price,
            wholesale_price=product.wholesale_price,
            unit=product.unit,
            attributes=product.attributes,
            image_url=product.image_url,
            is_active=product.is_active,
            quantity_on_hand=inventory.quantity_on_hand if inventory else None,
            product_type=product.product_type,
            show_in_catalog=product.show_in_catalog,
            cost_price=product.cost_price,
        )
