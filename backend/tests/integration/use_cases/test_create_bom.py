import uuid
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.dtos.bom_dto import BOMItemInputDTO, CreateBOMDTO
from src.application.exceptions import AlreadyExistsError, BusinessRuleViolation, NotFoundError
from src.application.use_cases.workshop.create_bom import CreateBOMUseCase
from src.domain.models.enums import ProductType
from src.domain.models.product import Product


def make_product(
    product_type: ProductType = ProductType.FINISHED_PRODUCT,
) -> Product:
    return Product(
        id=uuid.uuid4(), sku="TEST-001", name="Montura test",
        category_id=uuid.uuid4(), base_price=Decimal("50000"),
        unit="unidad", attributes={}, is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        product_type=product_type,
        show_in_catalog=False,
    )


def make_material(product_type: ProductType = ProductType.RAW_MATERIAL) -> Product:
    return Product(
        id=uuid.uuid4(), sku="MAT-001", name="Cuero vaqueta",
        category_id=uuid.uuid4(), base_price=Decimal("820"),
        unit="metro", attributes={}, is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        product_type=product_type,
        show_in_catalog=False,
        cost_price=Decimal("800"),
    )


@pytest.fixture
def setup_mocks():
    bom_repo = MagicMock()
    product_repo = MagicMock()
    bom_repo.get_bom_by_product_id = AsyncMock(return_value=None)
    bom_repo.create_bom = AsyncMock(side_effect=lambda b: b)
    bom_repo.get_bom_with_items = AsyncMock(return_value=(MagicMock(), []))
    return bom_repo, product_repo


@pytest.mark.asyncio
async def test_create_bom_success(setup_mocks):
    bom_repo, product_repo = setup_mocks
    product = make_product(ProductType.FINISHED_PRODUCT)
    material = make_material(ProductType.RAW_MATERIAL)

    product_repo.get_by_id = AsyncMock(side_effect=lambda pid: (
        product if pid == product.id else material
    ))

    uc = CreateBOMUseCase(bom_repo, product_repo)
    dto = CreateBOMDTO(
        output_quantity=Decimal("1"),
        items=[BOMItemInputDTO(
            material_id=material.id,
            quantity_required=Decimal("2.5"),
            scrap_factor=Decimal("0.08"),
        )],
    )
    await uc.execute(product.id, dto)
    bom_repo.create_bom.assert_called_once()


@pytest.mark.asyncio
async def test_create_bom_product_not_found(setup_mocks):
    bom_repo, product_repo = setup_mocks
    product_repo.get_by_id = AsyncMock(return_value=None)

    uc = CreateBOMUseCase(bom_repo, product_repo)
    dto = CreateBOMDTO(output_quantity=Decimal("1"), items=[])

    with pytest.raises(NotFoundError):
        await uc.execute(uuid.uuid4(), dto)


@pytest.mark.asyncio
async def test_create_bom_wrong_product_type(setup_mocks):
    bom_repo, product_repo = setup_mocks
    product = make_product(ProductType.RAW_MATERIAL)  # no es finished_product
    product_repo.get_by_id = AsyncMock(return_value=product)

    uc = CreateBOMUseCase(bom_repo, product_repo)
    dto = CreateBOMDTO(output_quantity=Decimal("1"), items=[])

    with pytest.raises(BusinessRuleViolation, match="finished_product"):
        await uc.execute(product.id, dto)


@pytest.mark.asyncio
async def test_create_bom_already_exists(setup_mocks):
    bom_repo, product_repo = setup_mocks
    product = make_product(ProductType.FINISHED_PRODUCT)
    existing_bom = MagicMock()
    existing_bom.is_active = True

    bom_repo.get_bom_by_product_id = AsyncMock(return_value=existing_bom)
    product_repo.get_by_id = AsyncMock(return_value=product)

    uc = CreateBOMUseCase(bom_repo, product_repo)
    dto = CreateBOMDTO(output_quantity=Decimal("1"), items=[])

    with pytest.raises(AlreadyExistsError):
        await uc.execute(product.id, dto)


@pytest.mark.asyncio
async def test_create_bom_material_wrong_type(setup_mocks):
    bom_repo, product_repo = setup_mocks
    product = make_product(ProductType.FINISHED_PRODUCT)
    bad_material = make_material(ProductType.RESALE)  # no puede ser material

    product_repo.get_by_id = AsyncMock(side_effect=lambda pid: (
        product if pid == product.id else bad_material
    ))

    uc = CreateBOMUseCase(bom_repo, product_repo)
    dto = CreateBOMDTO(
        output_quantity=Decimal("1"),
        items=[BOMItemInputDTO(material_id=bad_material.id, quantity_required=Decimal("1"))],
    )

    with pytest.raises(BusinessRuleViolation, match="raw_material"):
        await uc.execute(product.id, dto)
