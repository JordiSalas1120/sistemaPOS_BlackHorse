# Importar todos los modelos para que Alembic los detecte al generar migraciones
from src.infrastructure.database.orm_models.client_orm import ClientORM  # noqa: F401
from src.infrastructure.database.orm_models.category_orm import CategoryORM  # noqa: F401
from src.infrastructure.database.orm_models.product_orm import ProductORM  # noqa: F401
from src.infrastructure.database.orm_models.inventory_orm import InventoryORM, InventoryMovementORM  # noqa: F401
from src.infrastructure.database.orm_models.price_rule_orm import PriceRuleORM  # noqa: F401
from src.infrastructure.database.orm_models.sale_orm import SaleORM, SaleItemORM  # noqa: F401
from src.infrastructure.database.orm_models.audit_log_orm import AuditLogORM  # noqa: F401
from src.infrastructure.database.orm_models.bom_orm import BomItemORM, BomORM  # noqa: F401
from src.infrastructure.database.orm_models.production_order_orm import (  # noqa: F401
    ProductionOrderItemORM,
    ProductionOrderORM,
)
from src.infrastructure.database.orm_models.product_image_orm import ProductImageORM  # noqa: F401
