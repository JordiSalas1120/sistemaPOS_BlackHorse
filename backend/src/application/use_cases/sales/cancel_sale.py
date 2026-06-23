import uuid
from datetime import datetime, timezone
from uuid import UUID

from src.application.dtos.inventory_dto import AdjustStockDTO
from src.application.exceptions import BusinessRuleViolation, NotFoundError
from src.application.ports.repositories.audit_log_repository_port import AuditLogRepositoryPort
from src.application.ports.repositories.inventory_repository_port import InventoryRepositoryPort
from src.application.ports.repositories.product_repository_port import ProductRepositoryPort
from src.application.ports.repositories.sale_repository_port import SaleRepositoryPort
from src.application.use_cases.inventory.adjust_stock import AdjustStockUseCase
from src.domain.models.audit_log import AuditLog
from src.domain.models.enums import AuditAction, MovementType, SaleStatus
from src.domain.services.inventory_service import InventoryService


class CancelSaleUseCase:
    def __init__(
        self,
        sale_repo: SaleRepositoryPort,
        inventory_repo: InventoryRepositoryPort,
        product_repo: ProductRepositoryPort,
        audit_repo: AuditLogRepositoryPort,
        inventory_service: InventoryService,
    ):
        self._sale_repo = sale_repo
        self._inventory_repo = inventory_repo
        self._product_repo = product_repo
        self._audit_repo = audit_repo
        self._inventory_service = inventory_service

    async def execute(self, sale_id: UUID, actor: str = "system") -> None:
        sale = await self._sale_repo.get_by_id(sale_id)
        if not sale:
            raise NotFoundError("Venta", str(sale_id))
        if not sale.can_cancel():
            raise BusinessRuleViolation(
                f"No se puede cancelar una venta en estado '{sale.status}'."
            )

        sale.status = SaleStatus.CANCELLED
        sale.updated_at = datetime.now(timezone.utc)
        await self._sale_repo.update(sale)

        # Devolver stock
        for item in sale.items:
            adjust_uc = AdjustStockUseCase(
                self._inventory_repo, self._product_repo, self._audit_repo, self._inventory_service
            )
            await adjust_uc.execute(AdjustStockDTO(
                product_id=item.product_id,
                quantity_delta=item.quantity,
                movement_type=MovementType.RETURN,
                actor=actor,
                reference_id=sale_id,
                notes=f"Cancelación {sale.sale_number}",
            ))

        await self._audit_repo.create(AuditLog(
            id=uuid.uuid4(),
            entity_type="sale",
            entity_id=sale_id,
            action=AuditAction.CANCEL,
            actor=actor,
            payload={"sale_number": sale.sale_number, "total": str(sale.total)},
            created_at=datetime.now(timezone.utc),
        ))
