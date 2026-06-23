"""product_images table

Revision ID: 004
Revises: 003
Create Date: 2026-06-22
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── product_images ────────────────────────────────────────────────────────
    op.create_table(
        "product_images",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("alt_text", sa.String(200), nullable=True),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_primary", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Índice para listar imágenes de un producto en orden
    op.create_index(
        "ix_product_images_product_id_sort",
        "product_images",
        ["product_id", "sort_order"],
    )

    # Índice parcial: garantiza unicidad de is_primary=true por producto
    op.execute(
        """
        CREATE UNIQUE INDEX uq_product_images_primary
        ON product_images (product_id)
        WHERE is_primary = true
        """
    )

    # show_in_catalog ya fue agregada en la migración 002 (Sprint 1).
    # Se usa IF NOT EXISTS por idempotencia y se agrega el índice parcial de catálogo.
    op.execute(
        """
        ALTER TABLE products
        ADD COLUMN IF NOT EXISTS show_in_catalog BOOLEAN NOT NULL DEFAULT false
        """
    )
    op.create_index(
        "ix_products_show_in_catalog",
        "products",
        ["show_in_catalog"],
        postgresql_where=sa.text("show_in_catalog = true"),
    )


def downgrade() -> None:
    # NOTA: no se elimina la columna show_in_catalog porque es propiedad de la
    # migración 002 (Sprint 1). Aquí solo se revierte lo que agregó la 004.
    op.drop_index("ix_products_show_in_catalog", table_name="products")
    op.drop_index("uq_product_images_primary", table_name="product_images")
    op.drop_index("ix_product_images_product_id_sort", table_name="product_images")
    op.drop_table("product_images")
