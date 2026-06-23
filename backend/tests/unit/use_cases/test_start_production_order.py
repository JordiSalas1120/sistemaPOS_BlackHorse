from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4
from datetime import datetime, timezone

import pytest

from src.application.exceptions import InsufficientStockError
from src.application.use_cases.production.start_production_order import (
    StartProductionOrderUseCase,
)
from src.domain.models.enums import ProductionOrderStatus
from src.domain.models.inventory import Inventory
from src.domain.models.production_order import ProductionOrder, ProductionOrderItem


def _make_order(status=ProductionOrderStatus.DRAFT) -> ProductionOrder:
    return ProductionOrder(
        id=uuid4(),
        order_number="ORD-2026-00001",
        bom_id=uuid4(),
        finished_product_id=uuid4(),
        quantity_to_produce=Decimal("5"),
        produced_by="Test",
        status=status,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _make_inventory(product_id, qty: Decimal) -> Inventory:
    return Inventory(
        id=uuid4(),
        product_id=product_id,
        quantity_on_hand=qty,
        low_stock_threshold=Decimal("2"),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_start_raises_when_insufficient_stock():
    material_id = uuid4()
    item = ProductionOrderItem(
        id=uuid4(),
        order_id=uuid4(),
        material_id=material_id,
        quantity_required=Decimal("3.0"),  # 3 × 5 = 15 requeridos
        unit_cost_snapshot=Decimal("100"),
    )
    order = _make_order()

    order_repo = AsyncMock()
    order_repo.get_order_with_items.return_value = (order, [item])

    inventory_repo = AsyncMock()
    inventory_repo.get_by_product_id.return_value = _make_inventory(material_id, Decimal("10"))

    uc = StartProductionOrderUseCase(order_repo, inventory_repo)

    with pytest.raises(InsufficientStockError) as exc_info:
        await uc.execute(order.id)

    assert exc_info.value.product_id == str(material_id)
    assert exc_info.value.available == 10.0
    assert exc_info.value.requested == 15.0


@pytest.mark.asyncio
async def test_start_succeeds_when_stock_exact():
    material_id = uuid4()
    item = ProductionOrderItem(
        id=uuid4(),
        order_id=uuid4(),
        material_id=material_id,
        quantity_required=Decimal("2.0"),  # 2 × 5 = exactamente 10
        unit_cost_snapshot=Decimal("100"),
    )
    order = _make_order()

    order_repo = AsyncMock()
    order_repo.get_order_with_items.return_value = (order, [item])
    order_repo.update_order.return_value = order
    order_repo.get_order_items.return_value = [item]

    inventory_repo = AsyncMock()
    inventory_repo.get_by_product_id.return_value = _make_inventory(material_id, Decimal("10"))

    uc = StartProductionOrderUseCase(order_repo, inventory_repo)
    result = await uc.execute(order.id)

    assert result is not None
    order_repo.update_order.assert_called_once()
    called_order = order_repo.update_order.call_args[0][0]
    assert called_order.status == ProductionOrderStatus.IN_PROGRESS
    assert called_order.started_at is not None
