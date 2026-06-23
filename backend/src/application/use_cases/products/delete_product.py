import uuid
from datetime import datetime, timezone
from uuid import UUID

from src.application.exceptions import NotFoundError
from src.application.ports.repositories.audit_log_repository_port import AuditLogRepositoryPort
from src.application.ports.repositories.product_repository_port import ProductRepositoryPort
from src.domain.models.audit_log import AuditLog
from src.domain.models.enums import AuditAction


class DeleteProductUseCase:
    """Soft delete: marca el producto como inactivo en lugar de eliminarlo."""

    def __init__(self, product_repo: ProductRepositoryPort, audit_repo: AuditLogRepositoryPort):
        self._product_repo = product_repo
        self._audit_repo = audit_repo

    async def execute(self, product_id: UUID, actor: str = "system") -> None:
        product = await self._product_repo.get_by_id(product_id)
        if not product:
            raise NotFoundError("Producto", str(product_id))

        product.is_active = False
        product.updated_at = datetime.now(timezone.utc)
        await self._product_repo.update(product)

        await self._audit_repo.create(AuditLog(
            id=uuid.uuid4(),
            entity_type="product",
            entity_id=product_id,
            action=AuditAction.DELETE,
            actor=actor,
            payload={"before": {"sku": product.sku, "name": product.name}},
            created_at=datetime.now(timezone.utc),
        ))
