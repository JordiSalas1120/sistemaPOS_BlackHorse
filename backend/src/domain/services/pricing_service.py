from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from src.domain.models.enums import ClientType, DiscountType
from src.domain.models.price_rule import PriceRule


class PricingService:
    """
    Lógica pura de cálculo de precios y descuentos.
    No depende de base de datos ni de ningún framework.
    """

    def calculate_unit_price(
        self,
        base_price: Decimal,
        quantity: Decimal,
        client_type: ClientType,
        product_id: UUID,
        category_id: UUID,
        rules: list[PriceRule],
        now: datetime | None = None,
    ) -> tuple[Decimal, Decimal]:
        """
        Retorna (unit_price, discount_amount_per_unit).
        Aplica la regla de mayor prioridad que corresponda.
        """
        if now is None:
            now = datetime.now(timezone.utc)

        applicable = [
            r for r in rules
            if r.is_valid_now(now)
            and r.applies_to_client(client_type)
            and r.applies_to_quantity(quantity)
            and self._rule_matches_product(r, product_id, category_id)
        ]

        if not applicable:
            return base_price, Decimal("0")

        best_rule = max(applicable, key=lambda r: r.priority)
        discount = self._apply_discount(base_price, best_rule)
        return base_price - discount, discount

    def _rule_matches_product(
        self, rule: PriceRule, product_id: UUID, category_id: UUID
    ) -> bool:
        if rule.product_id is not None and rule.product_id != product_id:
            return False
        if rule.category_id is not None and rule.category_id != category_id:
            return False
        return True

    def _apply_discount(self, base_price: Decimal, rule: PriceRule) -> Decimal:
        if rule.discount_type == DiscountType.PERCENTAGE:
            return (base_price * rule.discount_value / Decimal("100")).quantize(Decimal("0.01"))
        return min(rule.discount_value, base_price)

    def calculate_cart_totals(
        self,
        items: list[dict],  # [{"unit_price": D, "quantity": D, "discount_amount": D}]
    ) -> dict:
        subtotal = Decimal("0")
        discount_total = Decimal("0")

        for item in items:
            line = item["unit_price"] * item["quantity"]
            subtotal += line
            discount_total += item["discount_amount"] * item["quantity"]

        total = subtotal - discount_total
        return {
            "subtotal": subtotal.quantize(Decimal("0.01")),
            "discount_total": discount_total.quantize(Decimal("0.01")),
            "tax_total": Decimal("0"),
            "total": total.quantize(Decimal("0.01")),
        }
