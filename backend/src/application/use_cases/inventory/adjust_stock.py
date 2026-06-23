import uuid
from datetime import datetime, timezone

from src.application.dtos.inventory_dto import AdjustStockDTO, MovementDTO
from src.application.exceptions import InsufficientStockError, NotFoundError
from src.application.ports.repositories.audit_log_repository_port import AuditLogRepositoryPort
from src.application.ports.repositories.inventory_repository_port import InventoryRepositoryPort
from src.application.ports.repositories.product_repository_port import ProductRepositoryPort
from src.domain.models.audit_log import AuditLog
from src.domain.models.enums import AuditAction
from src.domain.models.inventory import InventoryMovement
from src.domain.services.inventory_service import InventoryService


class AdjustStockUseCase:
    def __init__(
        self,
        inventory_repo: InventoryRepositoryPort,
        product_repo: ProductRepositoryPort,
        audit_repo: AuditLogRepositoryPort,
        inventory_service: InventoryService,
    ):
        self._inventory_repo = inventory_repo
        self._product_repo = product_repo
        self._audit_repo = audit_repo
        self._inventory_service = inventory_service

    async def execute(self, dto: AdjustStockDTO) -> MovementDTO:
        product = await self._product_repo.get_by_id(dto.product_id)
        if not product:
            raise NotFoundError("Producto", str(dto.product_id))

        inventory = await self._inventory_repo.get_by_product_id(dto.product_id)
        if not inventory:
            raise NotFoundError("Inventario", str(dto.product_id))

        # La lógica de validación de stock negativo vive en el servicio de dominio
        try:
            new_quantity = self._inventory_service.compute_new_quantity(
                inventory.quantity_on_hand, dto.quantity_delta
            )
        except ValueError as e:
            raise InsufficientStockError(
                str(dto.product_id),
                float(inventory.quantity_on_hand),
                float(abs(dto.quantity_delta)),
            ) from e

        quantity_before = inventory.quantity_on_hand
        inventory.quantity_on_hand = new_quantity
        inventory.updated_at = datetime.now(timezone.utc)
        await self._inventory_repo.update(inventory)

        movement = InventoryMovement(
            id=uuid.uuid4(),
            product_id=dto.product_id,
            movement_type=dto.movement_type,
            quantity_delta=dto.quantity_delta,
            quantity_before=quantity_before,
            quantity_after=new_quantity,
            reference_id=dto.reference_id,
            notes=dto.notes,
            created_by=dto.actor,
            created_at=datetime.now(timezone.utc),
        )
        saved_movement = await self._inventory_repo.create_movement(movement)

        await self._audit_repo.create(AuditLog(
            id=uuid.uuid4(),
            entity_type="inventory",
            entity_id=dto.product_id,
            action=AuditAction.UPDATE,
            actor=dto.actor,
            payload={
                "movement_type": dto.movement_type,
                "delta": str(dto.quantity_delta),
                "before": str(quantity_before),
                "after": str(new_quantity),
            },
            created_at=datetime.now(timezone.utc),
        ))

        return MovementDTO(
            id=saved_movement.id,
            product_id=saved_movement.product_id,
            movement_type=saved_movement.movement_type,
            quantity_delta=saved_movement.quantity_delta,
            quantity_before=saved_movement.quantity_before,
            quantity_after=saved_movement.quantity_after,
            created_by=saved_movement.created_by,
            created_at=saved_movement.created_at,
            notes=saved_movement.notes,
        )
