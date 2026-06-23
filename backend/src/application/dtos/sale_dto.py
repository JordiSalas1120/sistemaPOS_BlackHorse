from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from src.domain.models.enums import PaymentType, SaleStatus, SaleType


@dataclass
class SaleItemInputDTO:
    product_id: UUID
    quantity: Decimal


@dataclass
class CreateSaleDTO:
    items: list[SaleItemInputDTO]
    payment_type: PaymentType
    sale_type: SaleType = SaleType.RETAIL
    client_id: UUID | None = None
    notes: str | None = None


@dataclass
class SaleItemDTO:
    id: UUID
    sale_id: UUID
    product_id: UUID
    product_sku: str
    product_name: str
    quantity: Decimal
    unit_price: Decimal
    discount_amount: Decimal
    subtotal: Decimal


@dataclass
class SaleDTO:
    id: UUID
    sale_number: str
    sale_type: str
    status: str
    payment_type: str
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal
    total: Decimal
    sold_by: str
    created_at: datetime
    updated_at: datetime
    items: list[SaleItemDTO] = field(default_factory=list)
    client_id: UUID | None = None
    notes: str | None = None


@dataclass
class SaleListDTO:
    items: list[SaleDTO]
    total: int
    skip: int
    limit: int
