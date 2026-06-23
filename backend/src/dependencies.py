"""
Inyección de dependencias centralizada.
Los casos de uso reciben sus adaptadores aquí — nunca los instancian ellos mismos.
"""
from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.connection import async_session_factory

# ── Repositorios ──────────────────────────────────────────────────────────────
from src.infrastructure.adapters.postgres_repo.product_repository import ProductRepository
from src.infrastructure.adapters.postgres_repo.inventory_repository import InventoryRepository
from src.infrastructure.adapters.postgres_repo.category_repository import CategoryRepository
from src.infrastructure.adapters.postgres_repo.audit_log_repository import AuditLogRepository
from src.infrastructure.adapters.postgres_repo.client_repository import ClientRepository
from src.infrastructure.adapters.postgres_repo.sale_repository import SaleRepository
from src.infrastructure.adapters.postgres_repo.price_rule_repository import PriceRuleRepository
from src.infrastructure.adapters.postgres_repo.bom_repository import BOMRepository
from src.infrastructure.adapters.postgres_repo.workshop_product_repository import WorkshopProductRepository
from src.infrastructure.adapters.postgres_repo.production_order_repository import ProductionOrderRepository
from src.infrastructure.adapters.postgres_repo.catalog_repository import CatalogRepository
from src.infrastructure.adapters.postgres_repo.product_image_repository import ProductImageRepository
from src.application.ports.repositories.product_repository_port import ProductRepositoryPort
from src.application.ports.repositories.inventory_repository_port import InventoryRepositoryPort
from src.application.ports.repositories.category_repository_port import CategoryRepositoryPort
from src.application.ports.repositories.audit_log_repository_port import AuditLogRepositoryPort
from src.application.ports.repositories.client_repository_port import ClientRepositoryPort
from src.application.ports.repositories.sale_repository_port import SaleRepositoryPort
from src.application.ports.repositories.price_rule_repository_port import PriceRuleRepositoryPort
from src.application.ports.repositories.bom_repository_port import BOMRepositoryPort
from src.application.ports.repositories.workshop_product_repository_port import (
    WorkshopProductRepositoryPort,
)
from src.application.ports.repositories.production_order_repository_port import (
    ProductionOrderRepositoryPort,
)
from src.application.ports.repositories.catalog_repository_port import CatalogRepositoryPort
from src.application.ports.repositories.product_image_repository_port import (
    ProductImageRepositoryPort,
)

# ── Servicios de dominio ──────────────────────────────────────────────────────
from src.domain.services.inventory_service import InventoryService
from src.domain.services.pricing_service import PricingService
from src.domain.services.crm_tagging_service import CrmTaggingService


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provee una sesión de base de datos por request y garantiza su cierre."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_product_repo(session: AsyncSession = Depends(get_db_session)) -> ProductRepositoryPort:
    return ProductRepository(session)


def get_inventory_repo(session: AsyncSession = Depends(get_db_session)) -> InventoryRepositoryPort:
    return InventoryRepository(session)


def get_category_repo(session: AsyncSession = Depends(get_db_session)) -> CategoryRepositoryPort:
    return CategoryRepository(session)


def get_audit_repo(session: AsyncSession = Depends(get_db_session)) -> AuditLogRepositoryPort:
    return AuditLogRepository(session)


def get_client_repo(session: AsyncSession = Depends(get_db_session)) -> ClientRepositoryPort:
    return ClientRepository(session)


def get_sale_repo(session: AsyncSession = Depends(get_db_session)) -> SaleRepositoryPort:
    return SaleRepository(session)


def get_price_rule_repo(session: AsyncSession = Depends(get_db_session)) -> PriceRuleRepositoryPort:
    return PriceRuleRepository(session)


def get_bom_repo(session: AsyncSession = Depends(get_db_session)) -> BOMRepositoryPort:
    return BOMRepository(session)


def get_workshop_repo(session: AsyncSession = Depends(get_db_session)) -> WorkshopProductRepositoryPort:
    return WorkshopProductRepository(session)


def get_production_order_repo(
    session: AsyncSession = Depends(get_db_session),
) -> ProductionOrderRepositoryPort:
    return ProductionOrderRepository(session)


def get_catalog_repo(session: AsyncSession = Depends(get_db_session)) -> CatalogRepositoryPort:
    return CatalogRepository(session)


def get_product_image_repo(
    session: AsyncSession = Depends(get_db_session),
) -> ProductImageRepositoryPort:
    return ProductImageRepository(session)


def get_inventory_service() -> InventoryService:
    return InventoryService()


def get_pricing_service() -> PricingService:
    return PricingService()


def get_crm_tagging_service() -> CrmTaggingService:
    return CrmTaggingService()
