import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.base import Base


class ProductORM(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sku: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id"), nullable=False, index=True
    )
    base_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    wholesale_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="unidad")
    attributes: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    product_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="resale", index=True
    )
    show_in_catalog: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    cost_price: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    category: Mapped["CategoryORM"] = relationship("CategoryORM", back_populates="products")  # noqa: F821
    inventory: Mapped["InventoryORM"] = relationship("InventoryORM", back_populates="product", uselist=False)  # noqa: F821
    sale_items: Mapped[list["SaleItemORM"]] = relationship("SaleItemORM", back_populates="product", lazy="select")  # noqa: F821
    price_rules: Mapped[list["PriceRuleORM"]] = relationship("PriceRuleORM", back_populates="product", lazy="select")  # noqa: F821
    bom: Mapped["BomORM | None"] = relationship(  # noqa: F821
        "BomORM",
        back_populates="finished_product",
        foreign_keys="BomORM.finished_product_id",
        uselist=False,
    )
