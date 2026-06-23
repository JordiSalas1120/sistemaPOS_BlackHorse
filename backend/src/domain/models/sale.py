from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from src.domain.models.enums import PaymentType, SaleStatus, SaleType


@dataclass
class SaleItem:
    id: UUID
    sale_id: UUID
    product_id: UUID
    quantity: Decimal
    unit_price: Decimal           # snapshot del precio al momento de la venta
    discount_amount: Decimal = Decimal("0")

    @property
    def subtotal(self) -> Decimal:
        return (self.unit_price * self.quantity) - self.discount_amount


@dataclass
class Sale:
    id: UUID
    sale_number: str
    sale_type: SaleType
    status: SaleStatus
    payment_type: PaymentType
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal
    total: Decimal
    sold_by: str
    created_at: datetime
    updated_at: datetime
    items: list[SaleItem] = field(default_factory=list)
    client_id: UUID | None = None
    notes: str | None = None

    def can_cancel(self) -> bool:
        return self.status in (SaleStatus.DRAFT, SaleStatus.COMPLETED)

    def is_wholesale(self) -> bool:
        return self.sale_type == SaleType.WHOLESALE
