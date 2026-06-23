from decimal import Decimal
from uuid import uuid4

import pytest

from src.domain.models.production_order import ProductionOrderItem
from src.domain.services.production_cost_service import ProductionCostService


@pytest.fixture
def service() -> ProductionCostService:
    return ProductionCostService()


@pytest.fixture
def items() -> list[ProductionOrderItem]:
    return [
        ProductionOrderItem(
            id=uuid4(),
            order_id=uuid4(),
            material_id=uuid4(),
            quantity_required=Decimal("2.5"),
            unit_cost_snapshot=Decimal("350.00"),
        ),
        ProductionOrderItem(
            id=uuid4(),
            order_id=uuid4(),
            material_id=uuid4(),
            quantity_required=Decimal("1.0"),
            unit_cost_snapshot=Decimal("120.00"),
        ),
    ]


def test_material_cost_no_labor(service, items):
    """2 ítems, sin mano de obra. Costo = 2.5×350 + 1×120 = 875 + 120 = 995."""
    breakdown = service.calculate_production_cost(
        bom_items=items,
        material_prices={i.material_id: i.unit_cost_snapshot for i in items},
        quantity_to_produce=Decimal("1"),
    )
    assert breakdown.material_cost == Decimal("995.00")
    assert breakdown.labor_cost == Decimal("0")
    assert breakdown.total_cost == Decimal("995.00")
    assert breakdown.cost_per_unit == Decimal("995.00")


def test_cost_scales_with_quantity(service, items):
    """Producir 3 unidades: costo total = 995 × 3 = 2985."""
    breakdown = service.calculate_production_cost(
        bom_items=items,
        material_prices={i.material_id: i.unit_cost_snapshot for i in items},
        quantity_to_produce=Decimal("3"),
    )
    assert breakdown.total_cost == Decimal("2985.00")
    assert breakdown.cost_per_unit == Decimal("995.00")


def test_labor_cost_added(service, items):
    """60 minutos a 600 ARS/hora = 600 ARS de mano de obra."""
    breakdown = service.calculate_production_cost(
        bom_items=items,
        material_prices={i.material_id: i.unit_cost_snapshot for i in items},
        quantity_to_produce=Decimal("1"),
        labor_minutes=60,
        hourly_rate=Decimal("600.00"),
    )
    assert breakdown.labor_cost == Decimal("600.00")
    assert breakdown.total_cost == Decimal("1595.00")


def test_zero_quantity_returns_zero_cost_per_unit(service, items):
    """Evita ZeroDivisionError cuando quantity_to_produce es 0."""
    breakdown = service.calculate_production_cost(
        bom_items=items,
        material_prices={i.material_id: i.unit_cost_snapshot for i in items},
        quantity_to_produce=Decimal("0"),
    )
    assert breakdown.cost_per_unit == Decimal("0")


def test_market_price_overrides_snapshot(service, items):
    """Si se proveen precios actualizados, se usan en lugar del snapshot."""
    updated_prices = {
        items[0].material_id: Decimal("400.00"),  # subió de 350 a 400
        items[1].material_id: Decimal("120.00"),
    }
    breakdown = service.calculate_production_cost(
        bom_items=items,
        material_prices=updated_prices,
        quantity_to_produce=Decimal("1"),
    )
    expected_material = Decimal("2.5") * Decimal("400") + Decimal("1.0") * Decimal("120")
    assert breakdown.material_cost == expected_material
