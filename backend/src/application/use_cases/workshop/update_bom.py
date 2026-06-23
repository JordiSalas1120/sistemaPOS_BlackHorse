import uuid
from datetime import datetime, timezone

from src.application.dtos.bom_dto import BOMDTO, UpdateBOMDTO
from src.application.exceptions import BusinessRuleViolation, NotFoundError
from src.application.ports.repositories.bom_repository_port import BOMRepositoryPort
from src.application.ports.repositories.product_repository_port import ProductRepositoryPort
from src.domain.models.bom import BOMItem
from src.domain.models.enums import ProductType


class UpdateBOMUseCase:
    """
    Reemplaza completamente la BOM de un producto terminado:
    actualiza cabecera y sustituye todos los items (delete + insert).
    """

    def __init__(
        self,
        bom_repo: BOMRepositoryPort,
        product_repo: ProductRepositoryPort,
    ):
        self._bom_repo = bom_repo
        self._product_repo = product_repo

    async def execute(self, product_id: uuid.UUID, dto: UpdateBOMDTO) -> BOMDTO:
        # 1. Obtener BOM existente
        bom = await self._bom_repo.get_bom_by_product_id(product_id)
        if not bom:
            raise NotFoundError("BOM", f"producto {product_id}")

        # 2. Verificar materiales si se proporcionaron nuevos items
        if dto.items is not None:
            for item_dto in dto.items:
                material = await self._product_repo.get_by_id(item_dto.material_id)
                if not material:
                    raise NotFoundError("Material", str(item_dto.material_id))
                if material.product_type not in (ProductType.RAW_MATERIAL, ProductType.SUPPLY):
                    raise BusinessRuleViolation(
                        f"'{material.name}' (tipo: {material.product_type}) "
                        "no puede usarse como material en una receta."
                    )

        # 3. Actualizar campos de cabecera
        now = datetime.now(timezone.utc)
        if dto.output_quantity is not None:
            bom.output_quantity = dto.output_quantity
        if dto.labor_minutes is not None:
            bom.labor_minutes = dto.labor_minutes
        if dto.notes is not None:
            bom.notes = dto.notes
        if dto.is_active is not None:
            bom.is_active = dto.is_active
        bom.updated_at = now

        updated_bom = await self._bom_repo.update_bom(bom)

        # 4. Reemplazar items si se proporcionaron
        if dto.items is not None:
            _, old_items = await self._bom_repo.get_bom_with_items(bom.id)
            for old_item in old_items:
                await self._bom_repo.remove_bom_item(old_item.id)

            for idx, item_dto in enumerate(dto.items):
                new_item = BOMItem(
                    id=uuid.uuid4(),
                    bom_id=bom.id,
                    material_id=item_dto.material_id,
                    quantity_required=item_dto.quantity_required,
                    scrap_factor=item_dto.scrap_factor,
                    notes=item_dto.notes,
                    sort_order=idx,
                )
                await self._bom_repo.add_bom_item(new_item)

        _, final_items = await self._bom_repo.get_bom_with_items(bom.id)
        return BOMDTO.from_domain(updated_bom, final_items)
