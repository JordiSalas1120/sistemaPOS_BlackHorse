from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from src.domain.models.enums import ProductType, ProductUnit


@dataclass
class CreateProductDTO:
    name: str
    category_id: UUID
    base_price: Decimal
    sku: str | None = None  # None = generar automáticamente
    unit: ProductUnit = ProductUnit.UNIT
    description: str | None = None
    wholesale_price: Decimal | None = None
    image_url: str | None = None
    attributes: dict = field(default_factory=dict)
    low_stock_threshold: Decimal = Decimal("5")
    product_type: ProductType = ProductType.RESALE
    show_in_catalog: bool = False
    cost_price: Decimal | None = None


@dataclass
class UpdateProductDTO:
    name: str | None = None
    description: str | None = None
    category_id: UUID | None = None
    base_price: Decimal | None = None
    wholesale_price: Decimal | None = None
    unit: ProductUnit | None = None
    image_url: str | None = None
    attributes: dict | None = None
    is_active: bool | None = None
    product_type: ProductType | None = None
    show_in_catalog: bool | None = None
    cost_price: Decimal | None = None


@dataclass
class ProductDTO:
    id: UUID
    sku: str
    name: str
    category_id: UUID
    category_name: str
    base_price: Decimal
    unit: str
    attributes: dict
    is_active: bool
    description: str | None = None
    wholesale_price: Decimal | None = None
    image_url: str | None = None
    quantity_on_hand: Decimal | None = None
    product_type: str = "resale"
    show_in_catalog: bool = False
    cost_price: Decimal | None = None


@dataclass
class ProductListDTO:
    items: list[ProductDTO]
    total: int
    skip: int
    limit: int
