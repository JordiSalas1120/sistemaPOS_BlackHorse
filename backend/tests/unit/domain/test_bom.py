import uuid
from decimal import Decimal
from datetime import datetime, timezone

import pytest

from src.domain.models.bom import BOM, BOMItem


@pytest.fixture
def bom_with_items():
    bom_id = uuid.uuid4()
    mat1 = uuid.uuid4()
    mat2 = uuid.uuid4()
    mat3 = uuid.uuid4()

    items = [
        BOMItem(
            id=uuid.uuid4(), bom_id=bom_id,
            material_id=mat1,
            quantity_required=Decimal("2.500"),
            scrap_factor=Decimal("0.08"),   # → 2.7
        ),
        BOMItem(
            id=uuid.uuid4(), bom_id=bom_id,
            material_id=mat2,
            quantity_required=Decimal("6"),
            scrap_factor=Decimal("0"),      # → 6
        ),
        BOMItem(
            id=uuid.uuid4(), bom_id=bom_id,
            material_id=mat3,
            quantity_required=Decimal("0.150"),
            scrap_factor=Decimal("0.05"),   # → 0.1575
        ),
    ]

    bom = BOM(
        id=bom_id,
        finished_product_id=uuid.uuid4(),
        output_quantity=Decimal("1"),
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        items=items,
    )
    return bom, mat1, mat2, mat3


def test_effective_quantity_with_scrap():
    item = BOMItem(
        id=uuid.uuid4(), bom_id=uuid.uuid4(),
        material_id=uuid.uuid4(),
        quantity_required=Decimal("2.500"),
        scrap_factor=Decimal("0.08"),
    )
    assert item.effective_quantity == Decimal("2.700")


def test_effective_quantity_zero_scrap():
    item = BOMItem(
        id=uuid.uuid4(), bom_id=uuid.uuid4(),
        material_id=uuid.uuid4(),
        quantity_required=Decimal("6"),
        scrap_factor=Decimal("0"),
    )
    assert item.effective_quantity == Decimal("6")


def test_calculate_material_cost(bom_with_items):
    bom, mat1, mat2, mat3 = bom_with_items
    prices = {
        mat1: Decimal("820.00"),   # cuero: 2.7 × 820 = 2214.00
        mat2: Decimal("45.00"),    # hebilla: 6 × 45 = 270.00
        mat3: Decimal("350.00"),   # hilo: 0.1575 × 350 = 55.125
    }
    # Total = 2214.00 + 270.00 + 55.125 = 2539.125
    result = bom.calculate_material_cost(prices)
    assert result == Decimal("2539.125")


def test_cost_per_unit_single_output(bom_with_items):
    bom, mat1, mat2, mat3 = bom_with_items
    prices = {mat1: Decimal("820.00"), mat2: Decimal("45.00"), mat3: Decimal("350.00")}
    assert bom.cost_per_unit(prices) == Decimal("2539.125")


def test_cost_per_unit_batch_of_two(bom_with_items):
    bom, mat1, mat2, mat3 = bom_with_items
    bom.output_quantity = Decimal("2")
    prices = {mat1: Decimal("820.00"), mat2: Decimal("45.00"), mat3: Decimal("350.00")}
    assert bom.cost_per_unit(prices) == Decimal("2539.125") / Decimal("2")


def test_missing_material_raises_key_error(bom_with_items):
    bom, mat1, mat2, _ = bom_with_items
    prices = {mat1: Decimal("820.00"), mat2: Decimal("45.00")}
    # mat3 falta — debe lanzar KeyError
    with pytest.raises(KeyError):
        bom.calculate_material_cost(prices)


def test_calculate_cost_empty_bom():
    bom = BOM(
        id=uuid.uuid4(), finished_product_id=uuid.uuid4(),
        output_quantity=Decimal("1"), is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        items=[],
    )
    assert bom.calculate_material_cost({}) == Decimal("0")
