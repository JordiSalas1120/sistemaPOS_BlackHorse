"""workshop: product_type, BOM tables, new categories

Revision ID: 002
Revises: 001
Create Date: 2026-06-22
"""
from typing import Sequence, Union
import uuid

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ── Nuevas categorías para el taller ────────────────────────────────────────
NEW_CATEGORIES = [
    ("Cueros y Pieles",         "cueros-pieles"),
    ("Hebillería y Herrajes",   "hebilleria-herrajes"),
    ("Coronas y Adornos",       "coronas-adornos"),
    ("Hilos y Telas",           "hilos-telas"),
    ("Insumos de Taller",       "insumos-taller"),
    ("Monturas",                "monturas"),
    ("Hakimas y Jaquimas",      "hakimas-jaquimas"),
    ("Mantas y Sudaderos",      "mantas-sudaderos"),
    ("Riendas y Bridas",        "riendas-bridas"),
    ("Cinchería",               "cincheria"),
    ("Ganadería",               "ganaderia"),
    ("Pet Shop",                "pet-shop"),
    ("Herramientas de Taller",  "herramientas-taller"),
]


def upgrade() -> None:
    # ── 1. Extender tabla products ────────────────────────────────────────
    op.add_column(
        "products",
        sa.Column(
            "product_type",
            sa.String(20),
            nullable=False,
            server_default="resale",
        ),
    )
    op.add_column(
        "products",
        sa.Column(
            "show_in_catalog",
            sa.Boolean,
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "products",
        sa.Column(
            "cost_price",
            sa.Numeric(14, 2),
            nullable=True,
        ),
    )
    # Índice para filtrar por tipo de producto eficientemente
    op.create_index("ix_products_product_type", "products", ["product_type"])

    # ── 2. Crear tabla bom ────────────────────────────────────────────────
    op.create_table(
        "bom",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
        ),
        sa.Column(
            "finished_product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,   # un producto terminado → una BOM activa
        ),
        sa.Column(
            "output_quantity",
            sa.Numeric(12, 3),
            nullable=False,
            server_default="1",
            comment="Cantidad de producto terminado que produce esta receta",
        ),
        sa.Column(
            "labor_minutes",
            sa.Integer,
            nullable=True,
            comment="Minutos de mano de obra estimados por lote",
        ),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default="true",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_bom_finished_product_id", "bom", ["finished_product_id"])
    op.create_index("ix_bom_is_active", "bom", ["is_active"])

    # ── 3. Crear tabla bom_items ──────────────────────────────────────────
    op.create_table(
        "bom_items",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
        ),
        sa.Column(
            "bom_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bom.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "material_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="RESTRICT"),
            nullable=False,
            comment="Referencia a un producto de tipo raw_material o supply",
        ),
        sa.Column(
            "quantity_required",
            sa.Numeric(12, 3),
            nullable=False,
            comment="Cantidad neta requerida (sin scrap)",
        ),
        sa.Column(
            "scrap_factor",
            sa.Numeric(5, 4),
            nullable=False,
            server_default="0",
            comment="Factor de desperdicio: 0.05 = 5%. qty_total = qty × (1 + scrap)",
        ),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "sort_order",
            sa.Integer,
            nullable=False,
            server_default="0",
            comment="Orden de presentación dentro de la receta",
        ),
    )
    op.create_index("ix_bom_items_bom_id", "bom_items", ["bom_id"])
    op.create_index("ix_bom_items_material_id", "bom_items", ["material_id"])
    # Constraint: no duplicar el mismo material en la misma receta
    op.create_unique_constraint(
        "uq_bom_items_bom_material",
        "bom_items",
        ["bom_id", "material_id"],
    )

    # ── 4. Seed nuevas categorías ─────────────────────────────────────────
    for name, slug in NEW_CATEGORIES:
        op.execute(
            sa.text(
                """
                INSERT INTO categories (id, name, slug, created_at)
                VALUES (:id, :name, :slug, now())
                ON CONFLICT (slug) DO NOTHING
                """
            ).bindparams(id=str(uuid.uuid4()), name=name, slug=slug)
        )


def downgrade() -> None:
    # Eliminar en orden inverso para respetar FKs
    op.drop_table("bom_items")
    op.drop_table("bom")
    op.drop_index("ix_products_product_type", table_name="products")
    op.drop_column("products", "cost_price")
    op.drop_column("products", "show_in_catalog")
    op.drop_column("products", "product_type")
    # Las categorías no se eliminan en downgrade para evitar
    # borrar datos si ya hay productos asignados a ellas.
