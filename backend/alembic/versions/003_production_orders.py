"""production orders

Revision ID: 003
Revises: 002
Create Date: 2026-06-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── production_orders ───────────────────────────────────────────────────
    op.create_table(
        "production_orders",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("order_number", sa.String(30), nullable=False, unique=True),
        sa.Column(
            "bom_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bom.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "finished_product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("quantity_to_produce", sa.Numeric(12, 3), nullable=False),
        sa.Column(
            "quantity_produced",
            sa.Numeric(12, 3),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="draft",
        ),
        # Costo unitario calculado y congelado al completar la orden
        sa.Column("unit_cost_snapshot", sa.Numeric(14, 2), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("produced_by", sa.String(100), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_index("ix_production_orders_order_number", "production_orders", ["order_number"])
    op.create_index("ix_production_orders_status", "production_orders", ["status"])
    op.create_index("ix_production_orders_finished_product_id", "production_orders", ["finished_product_id"])
    op.create_index("ix_production_orders_bom_id", "production_orders", ["bom_id"])
    op.create_index("ix_production_orders_produced_by", "production_orders", ["produced_by"])
    op.create_index("ix_production_orders_created_at", "production_orders", ["created_at"])

    # ── production_order_items ──────────────────────────────────────────────
    op.create_table(
        "production_order_items",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("production_orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "material_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        # Snapshot de la cantidad requerida del BOM al crear la orden
        sa.Column("quantity_required", sa.Numeric(12, 3), nullable=False),
        # Cantidad realmente consumida al completar (puede diferir por merma real)
        sa.Column(
            "quantity_consumed",
            sa.Numeric(12, 3),
            nullable=False,
            server_default="0",
        ),
        # Precio del insumo al momento de crear la orden
        sa.Column("unit_cost_snapshot", sa.Numeric(14, 2), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
    )

    op.create_index("ix_production_order_items_order_id", "production_order_items", ["order_id"])
    op.create_index("ix_production_order_items_material_id", "production_order_items", ["material_id"])
    # Índice compuesto para consultas de "¿dónde se usó este material?"
    op.create_index(
        "ix_production_order_items_material_order",
        "production_order_items",
        ["material_id", "order_id"],
    )


def downgrade() -> None:
    op.drop_table("production_order_items")
    op.drop_table("production_orders")
