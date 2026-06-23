"""Tests para InventoryService."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.domain.models.inventory import Inventory
from src.domain.services.inventory_service import InventoryService


@pytest.fixture
def service():
    return InventoryService()


def make_inventory(quantity: Decimal, threshold: Decimal = Decimal("5")) -> Inventory:
    return Inventory(
        id=uuid.uuid4(),
        product_id=uuid.uuid4(),
        quantity_on_hand=quantity,
        low_stock_threshold=threshold,
        updated_at=datetime.now(timezone.utc),
    )


class TestCanFulfillOrder:
    def test_puede_cumplir_cuando_hay_stock_suficiente(self, service):
        inv = make_inventory(Decimal("10"))
        assert service.can_fulfill_order(inv, Decimal("10")) is True

    def test_puede_cumplir_cantidad_exacta(self, service):
        inv = make_inventory(Decimal("5"))
        assert service.can_fulfill_order(inv, Decimal("5")) is True

    def test_no_puede_cumplir_cuando_stock_insuficiente(self, service):
        inv = make_inventory(Decimal("3"))
        assert service.can_fulfill_order(inv, Decimal("5")) is False

    def test_no_puede_cumplir_con_stock_cero(self, service):
        inv = make_inventory(Decimal("0"))
        assert service.can_fulfill_order(inv, Decimal("1")) is False


class TestGetLowStockProducts:
    def test_detecta_productos_con_stock_bajo(self, service):
        low = make_inventory(Decimal("2"), threshold=Decimal("5"))
        ok = make_inventory(Decimal("10"), threshold=Decimal("5"))
        result = service.get_low_stock_products([low, ok])
        assert low in result
        assert ok not in result

    def test_incluye_stock_exactamente_igual_al_umbral(self, service):
        at_threshold = make_inventory(Decimal("5"), threshold=Decimal("5"))
        result = service.get_low_stock_products([at_threshold])
        assert at_threshold in result

    def test_lista_vacia(self, service):
        assert service.get_low_stock_products([]) == []


class TestComputeNewQuantity:
    def test_suma_entrada_de_stock(self, service):
        result = service.compute_new_quantity(Decimal("10"), Decimal("5"))
        assert result == Decimal("15")

    def test_resta_salida_de_stock(self, service):
        result = service.compute_new_quantity(Decimal("10"), Decimal("-3"))
        assert result == Decimal("7")

    def test_llega_a_cero_exacto(self, service):
        result = service.compute_new_quantity(Decimal("5"), Decimal("-5"))
        assert result == Decimal("0")

    def test_lanza_error_si_resulta_negativo(self, service):
        with pytest.raises(ValueError):
            service.compute_new_quantity(Decimal("3"), Decimal("-5"))
