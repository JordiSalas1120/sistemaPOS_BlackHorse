import uuid
from datetime import datetime, timezone
from decimal import Decimal

from src.application.dtos.product_dto import CreateProductDTO, ProductDTO
from src.application.exceptions import AlreadyExistsError, NotFoundError
from src.application.ports.repositories.audit_log_repository_port import AuditLogRepositoryPort
from src.application.ports.repositories.category_repository_port import CategoryRepositoryPort
from src.application.ports.repositories.inventory_repository_port import InventoryRepositoryPort
from src.application.ports.repositories.product_repository_port import ProductRepositoryPort
from src.domain.models.audit_log import AuditLog
from src.domain.models.enums import AuditAction
from src.domain.models.inventory import Inventory
from src.domain.models.product import Product


class CreateProductUseCase:
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

    CATEGORY_SLUG_PREFIXES = {
        "equino": "EQU",
        "bovino": "BOV",
        "accesorios": "ACC",
        "herreria": "HER",
        "cueros-pieles": "CUE",
        "hebilleria-herrajes": "HEB",
        "coronas-adornos": "COR",
        "hilos-telas": "HIL",
        "insumos-taller": "INS",
        "monturas": "MON",
        "hakimas-jaquimas": "JAQ",
        "mantas-sudaderos": "MAN",
        "riendas-bridas": "RIE",
        "cincheria": "CIN",
        "ganaderia": "GAN",
        "pet-shop": "PET",
        "herramientas-taller": "HTA",
    }

    @classmethod
    def _category_prefix(cls, slug: str) -> str:
        """Deriva prefijo de 3 letras del slug de categoría."""
        return cls.CATEGORY_SLUG_PREFIXES.get(slug, slug[:3].upper())

    async def _generate_sku(self, category_slug: str, category_id) -> str:
        """Genera SKU único: prefijo-NNNNN."""
        prefix = self._category_prefix(category_slug)
        count = await self._product_repo.count(active_only=False, category_id=category_id)
        candidate = f"{prefix}-{count + 1:05d}"
        # Garantizar unicidad en caso de colisión
        while await self._product_repo.get_by_sku(candidate):
            count += 1
            candidate = f"{prefix}-{count + 1:05d}"
        return candidate

    async def execute(self, dto: CreateProductDTO, actor: str = "system") -> ProductDTO:
        # Validar que la categoría existe
        category = await self._category_repo.get_by_id(dto.category_id)
        if not category:
            raise NotFoundError("Categoría", str(dto.category_id))

        # Generar SKU si no viene del cliente
        sku = dto.sku or await self._generate_sku(category.slug, dto.category_id)

        # Validar unicidad del SKU (solo si fue provisto manualmente)
        if dto.sku:
            existing = await self._product_repo.get_by_sku(sku)
            if existing:
                raise AlreadyExistsError("Producto", "SKU", sku)

        now = datetime.now(timezone.utc)
        product_id = uuid.uuid4()

        product = Product(
            id=product_id,
            sku=sku,
            name=dto.name,
            description=dto.description,
            category_id=dto.category_id,
            base_price=dto.base_price,
            wholesale_price=dto.wholesale_price,
            unit=dto.unit,
            attributes=dto.attributes,
            image_url=dto.image_url,
            is_active=True,
            created_at=now,
            updated_at=now,
            product_type=dto.product_type,
            show_in_catalog=dto.show_in_catalog,
            cost_price=dto.cost_price,
        )
        saved_product = await self._product_repo.create(product)

        # Crear registro de inventario con stock inicial en 0
        inventory = Inventory(
            id=uuid.uuid4(),
            product_id=product_id,
            quantity_on_hand=Decimal("0"),
            low_stock_threshold=dto.low_stock_threshold,
            updated_at=now,
        )
        await self._inventory_repo.create(inventory)

        # Auditoría
        await self._audit_repo.create(AuditLog(
            id=uuid.uuid4(),
            entity_type="product",
            entity_id=product_id,
            action=AuditAction.CREATE,
            actor=actor,
            payload={"after": {"sku": sku, "name": dto.name, "base_price": str(dto.base_price)}},
            created_at=now,
        ))

        return ProductDTO(
            id=saved_product.id,
            sku=saved_product.sku,
            name=saved_product.name,
            description=saved_product.description,
            category_id=saved_product.category_id,
            category_name=category.name,
            base_price=saved_product.base_price,
            wholesale_price=saved_product.wholesale_price,
            unit=saved_product.unit,
            attributes=saved_product.attributes,
            image_url=saved_product.image_url,
            is_active=saved_product.is_active,
            quantity_on_hand=Decimal("0"),
            product_type=saved_product.product_type,
            show_in_catalog=saved_product.show_in_catalog,
            cost_price=saved_product.cost_price,
        )
