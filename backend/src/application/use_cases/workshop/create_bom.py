import uuid
from datetime import datetime, timezone

from src.application.dtos.bom_dto import BOMDTO, CreateBOMDTO
from src.application.exceptions import AlreadyExistsError, BusinessRuleViolation, NotFoundError
from src.application.ports.repositories.bom_repository_port import BOMRepositoryPort
from src.application.ports.repositories.product_repository_port import ProductRepositoryPort
from src.domain.models.bom import BOM, BOMItem
from src.domain.models.enums import ProductType


class CreateBOMUseCase:
    def __init__(
        self,
        bom_repo: BOMRepositoryPort,
        product_repo: ProductRepositoryPort,
    ):
        self._bom_repo = bom_repo
        self._product_repo = product_repo

    async def execute(self, product_id: uuid.UUID, dto: CreateBOMDTO) -> BOMDTO:
        # 1. Verificar que el producto existe
        product = await self._product_repo.get_by_id(product_id)
        if not product:
            raise NotFoundError("Producto", str(product_id))

        # 2. Verificar que es un producto terminado
        if product.product_type != ProductType.FINISHED_PRODUCT:
            raise BusinessRuleViolation(
                f"Solo se puede crear BOM para productos de tipo 'finished_product'. "
                f"El producto '{product.name}' es de tipo '{product.product_type}'."
            )

        # 3. Verificar que no existe ya una BOM activa para este producto
        existing_bom = await self._bom_repo.get_bom_by_product_id(product_id)
        if existing_bom and existing_bom.is_active:
            raise AlreadyExistsError("BOM", "finished_product_id", str(product_id))

        # 4. Verificar que todos los materiales existen y son del tipo adecuado
        for item_dto in dto.items:
            material = await self._product_repo.get_by_id(item_dto.material_id)
            if not material:
                raise NotFoundError("Material", str(item_dto.material_id))
            if material.product_type not in (
                ProductType.RAW_MATERIAL,
                ProductType.SUPPLY,
            ):
                raise BusinessRuleViolation(
                    f"El producto '{material.name}' (tipo: {material.product_type}) "
                    f"no puede usarse como material en una receta. "
                    f"Solo se permiten 'raw_material' y 'supply'."
                )

        # 5. Construir entidades de dominio
        now = datetime.now(timezone.utc)
        bom_id = uuid.uuid4()

        items = [
            BOMItem(
                id=uuid.uuid4(),
                bom_id=bom_id,
                material_id=item_dto.material_id,
                quantity_required=item_dto.quantity_required,
                scrap_factor=item_dto.scrap_factor,
                notes=item_dto.notes,
                sort_order=idx,
            )
            for idx, item_dto in enumerate(dto.items)
        ]

        bom = BOM(
            id=bom_id,
            finished_product_id=product_id,
            output_quantity=dto.output_quantity,
            labor_minutes=dto.labor_minutes,
            notes=dto.notes,
            is_active=True,
            created_at=now,
            updated_at=now,
            items=items,
        )

        saved_bom = await self._bom_repo.create_bom(bom)
        _, saved_items = await self._bom_repo.get_bom_with_items(saved_bom.id)

        return BOMDTO.from_domain(saved_bom, saved_items)
