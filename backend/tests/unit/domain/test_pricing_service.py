"""Tests para PricingService — lógica pura, sin base de datos."""
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import pytest

from src.domain.models.enums import ClientType, DiscountType, PriceRuleType
from src.domain.models.price_rule import PriceRule
from src.domain.services.pricing_service import PricingService


@pytest.fixture
def service():
    return PricingService()


@pytest.fixture
def product_id():
    return uuid.uuid4()


@pytest.fixture
def category_id():
    return uuid.uuid4()


def make_rule(
    discount_value: Decimal,
    discount_type: DiscountType = DiscountType.PERCENTAGE,
    priority: int = 10,
    rule_type: PriceRuleType = PriceRuleType.CLIENT_TYPE,
    client_type_trigger: ClientType | None = None,
    min_quantity: Decimal | None = None,
    product_id=None,
    category_id=None,
    valid_from: datetime | None = None,
    valid_until: datetime | None = None,
) -> PriceRule:
    return PriceRule(
        id=uuid.uuid4(),
        name="Test rule",
        rule_type=rule_type,
        discount_type=discount_type,
        discount_value=discount_value,
        priority=priority,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        client_type_trigger=client_type_trigger,
        min_quantity=min_quantity,
        product_id=product_id,
        category_id=category_id,
        valid_from=valid_from,
        valid_until=valid_until,
    )


class TestCalculateUnitPrice:
    def test_sin_reglas_devuelve_precio_base(self, service, product_id, category_id):
        price, discount = service.calculate_unit_price(
            base_price=Decimal("1000"),
            quantity=Decimal("1"),
            client_type=ClientType.RETAIL,
            product_id=product_id,
            category_id=category_id,
            rules=[],
        )
        assert price == Decimal("1000")
        assert discount == Decimal("0")

    def test_descuento_porcentaje(self, service, product_id, category_id):
        rule = make_rule(discount_value=Decimal("10"), discount_type=DiscountType.PERCENTAGE)
        price, discount = service.calculate_unit_price(
            base_price=Decimal("1000"),
            quantity=Decimal("1"),
            client_type=ClientType.RETAIL,
            product_id=product_id,
            category_id=category_id,
            rules=[rule],
        )
        assert price == Decimal("900")
        assert discount == Decimal("100.00")

    def test_descuento_monto_fijo(self, service, product_id, category_id):
        rule = make_rule(discount_value=Decimal("150"), discount_type=DiscountType.FIXED_AMOUNT)
        price, discount = service.calculate_unit_price(
            base_price=Decimal("1000"),
            quantity=Decimal("1"),
            client_type=ClientType.RETAIL,
            product_id=product_id,
            category_id=category_id,
            rules=[rule],
        )
        assert price == Decimal("850")
        assert discount == Decimal("150")

    def test_regla_por_tipo_cliente_no_aplica_a_otro_tipo(self, service, product_id, category_id):
        rule = make_rule(
            discount_value=Decimal("20"),
            client_type_trigger=ClientType.WHOLESALE,
        )
        price, discount = service.calculate_unit_price(
            base_price=Decimal("1000"),
            quantity=Decimal("1"),
            client_type=ClientType.RETAIL,  # No es mayorista
            product_id=product_id,
            category_id=category_id,
            rules=[rule],
        )
        assert price == Decimal("1000")
        assert discount == Decimal("0")

    def test_regla_por_cantidad_minima_no_aplica_si_cantidad_insuficiente(self, service, product_id, category_id):
        rule = make_rule(discount_value=Decimal("15"), min_quantity=Decimal("10"))
        price, _ = service.calculate_unit_price(
            base_price=Decimal("1000"),
            quantity=Decimal("5"),  # Menor a min_quantity=10
            client_type=ClientType.RETAIL,
            product_id=product_id,
            category_id=category_id,
            rules=[rule],
        )
        assert price == Decimal("1000")

    def test_regla_por_cantidad_minima_aplica_si_cantidad_suficiente(self, service, product_id, category_id):
        rule = make_rule(discount_value=Decimal("15"), min_quantity=Decimal("10"))
        price, _ = service.calculate_unit_price(
            base_price=Decimal("1000"),
            quantity=Decimal("10"),
            client_type=ClientType.RETAIL,
            product_id=product_id,
            category_id=category_id,
            rules=[rule],
        )
        assert price == Decimal("850")

    def test_se_aplica_regla_de_mayor_prioridad(self, service, product_id, category_id):
        low_priority = make_rule(discount_value=Decimal("5"), priority=5)
        high_priority = make_rule(discount_value=Decimal("20"), priority=20)
        price, _ = service.calculate_unit_price(
            base_price=Decimal("1000"),
            quantity=Decimal("1"),
            client_type=ClientType.RETAIL,
            product_id=product_id,
            category_id=category_id,
            rules=[low_priority, high_priority],
        )
        assert price == Decimal("800")

    def test_regla_vencida_no_aplica(self, service, product_id, category_id):
        expired_rule = make_rule(
            discount_value=Decimal("10"),
            valid_until=datetime.now(timezone.utc) - timedelta(days=1),
        )
        price, _ = service.calculate_unit_price(
            base_price=Decimal("1000"),
            quantity=Decimal("1"),
            client_type=ClientType.RETAIL,
            product_id=product_id,
            category_id=category_id,
            rules=[expired_rule],
        )
        assert price == Decimal("1000")

    def test_regla_futura_no_aplica(self, service, product_id, category_id):
        future_rule = make_rule(
            discount_value=Decimal("10"),
            valid_from=datetime.now(timezone.utc) + timedelta(days=1),
        )
        price, _ = service.calculate_unit_price(
            base_price=Decimal("1000"),
            quantity=Decimal("1"),
            client_type=ClientType.RETAIL,
            product_id=product_id,
            category_id=category_id,
            rules=[future_rule],
        )
        assert price == Decimal("1000")

    def test_regla_especifica_de_producto_no_aplica_a_otro(self, service, product_id, category_id):
        other_product = uuid.uuid4()
        rule = make_rule(discount_value=Decimal("10"), product_id=other_product)
        price, _ = service.calculate_unit_price(
            base_price=Decimal("1000"),
            quantity=Decimal("1"),
            client_type=ClientType.RETAIL,
            product_id=product_id,
            category_id=category_id,
            rules=[rule],
        )
        assert price == Decimal("1000")

    def test_descuento_fijo_no_supera_precio_base(self, service, product_id, category_id):
        rule = make_rule(discount_value=Decimal("9999"), discount_type=DiscountType.FIXED_AMOUNT)
        price, discount = service.calculate_unit_price(
            base_price=Decimal("100"),
            quantity=Decimal("1"),
            client_type=ClientType.RETAIL,
            product_id=product_id,
            category_id=category_id,
            rules=[rule],
        )
        assert price == Decimal("0")
        assert discount == Decimal("100")


class TestCalculateCartTotals:
    def test_totales_sin_descuento(self, service):
        items = [
            {"unit_price": Decimal("100"), "quantity": Decimal("2"), "discount_amount": Decimal("0")},
            {"unit_price": Decimal("50"), "quantity": Decimal("1"), "discount_amount": Decimal("0")},
        ]
        result = service.calculate_cart_totals(items)
        assert result["subtotal"] == Decimal("250.00")
        assert result["discount_total"] == Decimal("0.00")
        assert result["total"] == Decimal("250.00")

    def test_totales_con_descuento(self, service):
        items = [
            {"unit_price": Decimal("100"), "quantity": Decimal("2"), "discount_amount": Decimal("10")},
        ]
        result = service.calculate_cart_totals(items)
        assert result["subtotal"] == Decimal("200.00")
        assert result["discount_total"] == Decimal("20.00")
        assert result["total"] == Decimal("180.00")
