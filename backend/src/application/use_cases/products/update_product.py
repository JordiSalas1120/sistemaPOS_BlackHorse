import uuid
from datetime import datetime, timezone
from uuid import UUID

from src.application.dtos.product_dto import ProductDTO, UpdateProductDTO
from src.application.exceptions import NotFoundError
from src.application.ports.repositories.audit_log_repository_port import AuditLogRepositoryPort
from src.application.ports.repositories.category_repository_port import CategoryRepositoryPort
from src.application.ports.repositories.inventory_repository_port import InventoryRepositoryPort
from src.application.ports.repositories.product_repository_port import ProductRepositoryPort
from src.domain.models.audit_log import AuditLog
from src.domain.models.enums import AuditAction


class UpdateProductUseCase:
    def __init__(
        self,
        product_repo: ProductRepositoryPort,
        category_repo: CategoryRepositoryPort,
        inventory_repo: InventoryRepositoryPort,
        audit_repo: AuditLogRepositoryPort,
    ):
        self._product_repo = product_repo
        self._category_repo = category_repo
        self._inventory_repo = inventory_repo
        self._audit_repo = audit_repo

    async def execute(self, product_id: UUID, dto: UpdateProductDTO, actor: str = "system") -> ProductDTO:
        product = await self._product_repo.get_by_id(product_id)
        if not product:
            raise NotFoundError("Producto", str(product_id))

        before = {"name": product.name, "base_price": str(product.base_price), "is_active": product.is_active}

        if dto.name is not None:
            product.name = dto.name
        if dto.description is not None:
            product.description = dto.description
        if dto.category_id is not None:
            category = await self._category_repo.get_by_id(dto.category_id)
            if not category:
                raise NotFoundError("Categoría", str(dto.category_id))
            product.category_id = dto.category_id
        if dto.base_price is not None:
            product.base_price = dto.base_price
        if dto.wholesale_price is not None:
            product.wholesale_price = dto.wholesale_price
        if dto.unit is not None:
            product.unit = dto.unit
        if dto.image_url is not None:
            product.image_url = dto.image_url
        if dto.attributes is not None:
            product.attributes = dto.attributes
        if dto.is_active is not None:
            product.is_active = dto.is_active
        if dto.product_type is not None:
            product.product_type = dto.product_type
        if dto.show_in_catalog is not None:
            product.show_in_catalog = dto.show_in_catalog
        if dto.cost_price is not None:
            product.cost_price = dto.cost_price

        product.updated_at = datetime.now(timezone.utc)
        saved = await self._product_repo.update(product)

        category = await self._category_repo.get_by_id(saved.category_id)
        inventory = await self._inventory_repo.get_by_product_id(product_id)

        await self._audit_repo.create(AuditLog(
            id=uuid.uuid4(),
            entity_type="product",
            entity_id=product_id,
            action=AuditAction.UPDATE,
            actor=actor,
            payload={"before": before, "after": {"name": saved.name, "base_price": str(saved.base_price)}},
            created_at=datetime.now(timezone.utc),
        ))

        return ProductDTO(
            id=saved.id,
            sku=saved.sku,
            name=saved.name,
            description=saved.description,
            category_id=saved.category_id,
            category_name=category.name if category else "—",
            base_price=saved.base_price,
            wholesale_price=saved.wholesale_price,
            unit=saved.unit,
            attributes=saved.attributes,
            image_url=saved.image_url,
            is_active=saved.is_active,
            quantity_on_hand=inventory.quantity_on_hand if inventory else None,
            product_type=saved.product_type,
            show_in_catalog=saved.show_in_catalog,
            cost_price=saved.cost_price,
        )
