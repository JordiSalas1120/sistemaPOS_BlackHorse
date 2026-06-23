# Sprint 1 — Módulo Taller: Materias Primas, Productos Terminados y BOM

**Proyecto**: CMS/CRM Talabartería  
**Sprint**: 1  
**Fecha**: 2026-06-22  
**Estado**: Especificación técnica lista para implementación

---

## 1. Objetivo y Alcance

### Qué entra en este Sprint

- Distinguir los tres universos de artículos que maneja el taller:
  - **Materias primas** (cueros, herrajes, hilos, etc.) — se compran, consumen en producción y requieren control de stock.
  - **Productos terminados** (monturas, jaquimas, riendas, etc.) — se fabrican a partir de una receta y se venden.
  - **Insumos / herramientas** — consumibles o activos del taller que no se venden al público.
- Agregar el campo `product_type` a la tabla `products` (valores: `raw_material`, `finished_product`, `tool`, `supply`, `resale`). Los productos existentes quedan con `resale` por defecto.
- Agregar `show_in_catalog` y `cost_price` a `products`.
- Crear tablas `bom` (Bill of Materials — cabecera de receta) y `bom_items` (líneas de receta).
- Ampliar el catálogo de categorías con 13 nuevas categorías orientadas al taller.
- CRUD completo de BOM vía endpoint `/api/v1/workshop/`.
- Filtro `?product_type=` en el endpoint existente `GET /api/v1/products`.
- Extensión del formulario de producto en el frontend (`ProductForm.tsx`).
- Nueva página `/dashboard/taller` con dos pestañas y componente `BOMEditor`.

### Qué NO entra en este Sprint

- Proceso de producción / órdenes de fabricación (quedará para Sprint 2).
- Descuento automático de stock de materias primas al registrar una venta de producto terminado.
- Costos de mano de obra integrados al precio de venta.
- Historial de versiones de BOM.
- Cálculo de rentabilidad bruta (margen = precio_venta − costo_BOM).
- Integración con el módulo de compras.
- Imágenes de productos terminados con su receta.

---

## 2. Decisiones de Arquitectura

### Por qué se extiende `products` con `product_type` en lugar de tabla separada

1. **Datos compartidos dominan sobre datos exclusivos.** SKU, nombre, categoría, precios, unidad, atributos JSONB, inventario e imagen son comunes a todos los tipos. Una tabla separada duplicaría estas columnas o forzaría JOINs en cada consulta de listado.
2. **Inventory ya apunta a `products`.** Crear una tabla `raw_materials` distinta obligaría a romper la FK de `inventory` o duplicar el módulo de movimientos de stock.
3. **Price rules y sale_items también referencian `products`.** Mantener una sola tabla preserva la integridad referencial sin cambios en migraciones previas.
4. **Discriminator pattern (single-table inheritance ligero).** `product_type VARCHAR(20)` actúa como discriminador; los campos opcionales (`cost_price`, `show_in_catalog`) solo son relevantes según el tipo. Esta es la misma estrategia que usa, por ejemplo, Django con `proxy models`.
5. **Migración sin riesgo.** `ALTER TABLE products ADD COLUMN product_type VARCHAR(20) DEFAULT 'resale'` no toca filas existentes.

### Por qué `bom` es una tabla con header + items (no JSONB en `products`)

1. **Relaciones navegables.** Cada `bom_item` tiene FK a `products` (la materia prima), lo que permite consultar "¿en qué recetas se usa este cuero?" con un JOIN simple.
2. **Consistencia referencial garantizada por la base de datos.** Un JSONB no puede tener FK; si se elimina una materia prima referenciada, el JSONB quedaría huérfano silenciosamente.
3. **Escalabilidad de consultas de costo.** Para calcular el costo de un lote de producción se necesita unir precios actuales de múltiples materiales; hacerlo sobre filas es más eficiente y legible que desempaquetar JSONB.
4. **`bom` tiene lifecycle propio.** La cabecera almacena `output_quantity`, `labor_minutes`, `is_active` y timestamps — metadatos que no pertenecen a `products`.

### Convenciones de nombrado

| Concepto | Convención | Ejemplo |
|----------|-----------|---------|
| Archivos Python | `snake_case.py` | `create_bom.py` |
| Clases dominio | `PascalCase` | `BOM`, `BOMItem` |
| ORM models | `PascalCaseORM` | `BomORM`, `BomItemORM` |
| Ports | `PascalCaseRepositoryPort` | `BOMRepositoryPort` |
| Use cases | `VerbNounUseCase` | `CreateBOMUseCase` |
| DTOs | `VerbNounDTO` / `NounDTO` | `CreateBOMDTO`, `BOMDTO` |
| Schemas API | `NounRequest` / `NounResponse` | `BOMCreateRequest`, `BOMResponse` |
| Enums Python | `StrEnum` miembros en `UPPER_SNAKE` | `ProductType.RAW_MATERIAL` |
| TypeScript types | `PascalCase` interfaces | `BOMItem`, `WorkshopProduct` |
| Endpoints | kebab-case plural | `/workshop/finished-products` |
| Slugs categoría | kebab-case sin tildes | `cueros-pieles` |

---

## 3. Migración 002 — SQL Completo

Archivo: `backend/alembic/versions/002_workshop_bom.py`

```python
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
            f"""
            INSERT INTO categories (id, name, slug, created_at)
            VALUES ('{uuid.uuid4()}', '{name}', '{slug}', now())
            ON CONFLICT (slug) DO NOTHING
            """
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
```

---

## 4. Modelos de Dominio

Archivo: `backend/src/domain/models/enums.py` — agregar al final del archivo existente:

```python
class ProductType(StrEnum):
    RAW_MATERIAL     = "raw_material"      # materia prima: cuero, hebilla, hilo
    FINISHED_PRODUCT = "finished_product"  # producto fabricado en taller: montura, jaquima
    TOOL             = "tool"              # herramienta del taller (no se vende)
    SUPPLY           = "supply"            # insumo consumible: adhesivo, cera
    RESALE           = "resale"            # artículo para reventa sin transformación
```

Archivo: `backend/src/domain/models/product.py` — agregar campos al dataclass `Product` existente:

```python
# Agregar estas líneas al dataclass Product (con valores por defecto al final):
product_type: "ProductType" = ProductType.RESALE  # noqa: F821 — evitar import circular
show_in_catalog: bool = False
cost_price: Decimal | None = None
```

Archivo: `backend/src/domain/models/bom.py` — archivo nuevo:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass
class BOMItem:
    """Línea de una receta de producción."""
    id: UUID
    bom_id: UUID
    material_id: UUID
    quantity_required: Decimal        # cantidad neta requerida
    sort_order: int = 0
    scrap_factor: Decimal = Decimal("0")  # 0.05 = 5% de desperdicio
    notes: str | None = None

    @property
    def effective_quantity(self) -> Decimal:
        """Cantidad real a consumir incluyendo desperdicio: qty × (1 + scrap)."""
        return self.quantity_required * (Decimal("1") + self.scrap_factor)


@dataclass
class BOM:
    """
    Bill of Materials — receta de producción para un producto terminado.
    Una BOM pertenece a exactamente un producto de tipo finished_product.
    """
    id: UUID
    finished_product_id: UUID
    output_quantity: Decimal          # cuántas unidades produce esta receta
    is_active: bool
    created_at: datetime
    updated_at: datetime
    labor_minutes: int | None = None  # mano de obra estimada en minutos por lote
    notes: str | None = None
    items: list[BOMItem] = field(default_factory=list)

    def calculate_material_cost(self, prices: dict[UUID, Decimal]) -> Decimal:
        """
        Calcula el costo total de materiales para producir `output_quantity` unidades.

        Args:
            prices: Mapa { material_id → costo_unitario } con los precios actuales
                    de cada materia prima (normalmente cost_price del producto o base_price).

        Returns:
            Costo total de materiales para el lote completo (output_quantity unidades).
            Para obtener el costo por unidad: resultado / output_quantity.

        Raises:
            KeyError: Si algún material_id no está presente en el dict `prices`.
                      El caller debe asegurar que todos los materiales estén incluidos.
        """
        total = Decimal("0")
        for item in self.items:
            unit_price = prices[item.material_id]
            total += item.effective_quantity * unit_price
        return total

    def cost_per_unit(self, prices: dict[UUID, Decimal]) -> Decimal:
        """Costo de materiales por unidad de producto terminado."""
        if self.output_quantity == Decimal("0"):
            return Decimal("0")
        return self.calculate_material_cost(prices) / self.output_quantity
```

---

## 5. ORM Models

### 5.1 Modificar `ProductORM`

Archivo: `backend/src/infrastructure/database/orm_models/product_orm.py`

Agregar las tres columnas nuevas dentro de la clase `ProductORM`, después de `is_active`:

```python
product_type: Mapped[str] = mapped_column(
    String(20), nullable=False, default="resale", index=True
)
show_in_catalog: Mapped[bool] = mapped_column(
    Boolean, nullable=False, default=False
)
cost_price: Mapped[Decimal | None] = mapped_column(
    Numeric(14, 2), nullable=True
)
```

Agregar la relación inversa hacia BOM (al final de las relaciones de `ProductORM`):

```python
bom: Mapped["BomORM | None"] = relationship(
    "BomORM",
    back_populates="finished_product",
    foreign_keys="BomORM.finished_product_id",
    uselist=False,
)
```

### 5.2 Nuevo archivo `bom_orm.py`

Archivo: `backend/src/infrastructure/database/orm_models/bom_orm.py`

```python
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.base import Base


class BomORM(Base):
    __tablename__ = "bom"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    finished_product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
        index=True,
    )
    output_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), nullable=False, default=Decimal("1")
    )
    labor_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relaciones
    finished_product: Mapped["ProductORM"] = relationship(  # noqa: F821
        "ProductORM",
        back_populates="bom",
        foreign_keys=[finished_product_id],
    )
    items: Mapped[list["BomItemORM"]] = relationship(
        "BomItemORM",
        back_populates="bom",
        cascade="all, delete-orphan",
        order_by="BomItemORM.sort_order",
        lazy="select",
    )


class BomItemORM(Base):
    __tablename__ = "bom_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    bom_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bom.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    quantity_required: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), nullable=False
    )
    scrap_factor: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, default=Decimal("0")
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relaciones
    bom: Mapped["BomORM"] = relationship("BomORM", back_populates="items")
    material: Mapped["ProductORM"] = relationship(  # noqa: F821
        "ProductORM",
        foreign_keys=[material_id],
        lazy="select",
    )
```

Agregar los imports en `backend/src/infrastructure/database/orm_models/__init__.py`:

```python
from src.infrastructure.database.orm_models.bom_orm import BomItemORM, BomORM
```

---

## 6. Puerto: BOMRepositoryPort

Archivo: `backend/src/application/ports/repositories/bom_repository_port.py`

```python
from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.models.bom import BOM, BOMItem


class BOMRepositoryPort(ABC):
    """Puerto abstracto para persistencia de BOM y sus items."""

    @abstractmethod
    async def get_bom_by_product_id(self, product_id: UUID) -> BOM | None:
        """
        Retorna la BOM activa asociada al producto terminado indicado.
        No incluye los items; usar get_bom_with_items para eso.
        """
        ...

    @abstractmethod
    async def create_bom(self, bom: BOM) -> BOM:
        """
        Persiste una nueva BOM. Los items en bom.items se persisten en cascada.
        Retorna la entidad con id y timestamps asignados por la BD.
        """
        ...

    @abstractmethod
    async def update_bom(self, bom: BOM) -> BOM:
        """
        Actualiza los campos de la cabecera (output_quantity, labor_minutes, notes, is_active).
        NO reemplaza los items — usar add/update/remove_bom_item para eso.
        """
        ...

    @abstractmethod
    async def delete_bom(self, bom_id: UUID) -> None:
        """
        Elimina la BOM y sus items en cascada (CASCADE definido en FK de bom_items).
        Lanza NotFoundError si bom_id no existe.
        """
        ...

    @abstractmethod
    async def get_bom_with_items(self, bom_id: UUID) -> tuple[BOM, list[BOMItem]]:
        """
        Retorna la BOM y su lista de items (eager load).
        Lanza NotFoundError si bom_id no existe.
        """
        ...

    @abstractmethod
    async def add_bom_item(self, item: BOMItem) -> BOMItem:
        """
        Agrega un nuevo item a una BOM existente.
        Lanza AlreadyExistsError si (bom_id, material_id) ya existe.
        Lanza NotFoundError si bom_id o material_id no existen.
        """
        ...

    @abstractmethod
    async def remove_bom_item(self, bom_item_id: UUID) -> None:
        """
        Elimina el item indicado.
        Lanza NotFoundError si bom_item_id no existe.
        """
        ...

    @abstractmethod
    async def update_bom_item(self, item: BOMItem) -> BOMItem:
        """
        Actualiza quantity_required, scrap_factor, notes y sort_order del item.
        Lanza NotFoundError si item.id no existe.
        """
        ...
```

---

## 7. Puerto: WorkshopProductRepositoryPort

Archivo: `backend/src/application/ports/repositories/workshop_product_repository_port.py`

```python
from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.models.enums import ProductType
from src.domain.models.product import Product


class WorkshopProductRepositoryPort(ABC):
    """
    Métodos adicionales sobre products para consultas específicas del taller.
    Los adaptadores PostgreSQL implementan esta interfaz extendiendo (o componiendo)
    el ProductRepository existente.
    """

    @abstractmethod
    async def list_raw_materials(
        self,
        skip: int = 0,
        limit: int = 50,
        category_id: UUID | None = None,
        search: str | None = None,
        active_only: bool = True,
    ) -> list[Product]:
        """
        Lista productos con product_type = 'raw_material'.
        search: coincidencia parcial (ILIKE) en name o sku.
        """
        ...

    @abstractmethod
    async def count_raw_materials(
        self,
        category_id: UUID | None = None,
        search: str | None = None,
        active_only: bool = True,
    ) -> int: ...

    @abstractmethod
    async def list_finished_products(
        self,
        skip: int = 0,
        limit: int = 50,
        category_id: UUID | None = None,
        search: str | None = None,
        active_only: bool = True,
    ) -> list[Product]:
        """Lista productos con product_type = 'finished_product'."""
        ...

    @abstractmethod
    async def count_finished_products(
        self,
        category_id: UUID | None = None,
        search: str | None = None,
        active_only: bool = True,
    ) -> int: ...

    @abstractmethod
    async def list_by_type(
        self,
        product_type: ProductType,
        skip: int = 0,
        limit: int = 50,
        active_only: bool = True,
    ) -> list[Product]:
        """Genérico: lista por cualquier product_type."""
        ...

    @abstractmethod
    async def count_by_type(
        self,
        product_type: ProductType,
        active_only: bool = True,
    ) -> int: ...
```

---

## 8. Use Cases

### 8.1 `create_bom.py`

Archivo: `backend/src/application/use_cases/workshop/create_bom.py`

```python
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from src.application.dtos.bom_dto import BOMItemInputDTO, CreateBOMDTO, BOMDTO
from src.application.exceptions import AlreadyExistsError, BusinessRuleViolation, NotFoundError
from src.application.ports.repositories.bom_repository_port import BOMRepositoryPort
from src.application.ports.repositories.product_repository_port import ProductRepositoryPort
from src.domain.models.bom import BOM, BOMItem
from src.domain.models.enums import ProductType


class CreateBOMUseCase:
    def __init__(
        self,
        bom_repo: BOMRepositoryPort,
        product_repo: ProductRepositoryPort,
    ):
        self._bom_repo = bom_repo
        self._product_repo = product_repo

    async def execute(self, product_id: uuid.UUID, dto: CreateBOMDTO) -> BOMDTO:
        # 1. Verificar que el producto existe
        product = await self._product_repo.get_by_id(product_id)
        if not product:
            raise NotFoundError("Producto", str(product_id))

        # 2. Verificar que es un producto terminado
        if product.product_type != ProductType.FINISHED_PRODUCT:
            raise BusinessRuleViolation(
                f"Solo se puede crear BOM para productos de tipo 'finished_product'. "
                f"El producto '{product.name}' es de tipo '{product.product_type}'."
            )

        # 3. Verificar que no existe ya una BOM activa para este producto
        existing_bom = await self._bom_repo.get_bom_by_product_id(product_id)
        if existing_bom and existing_bom.is_active:
            raise AlreadyExistsError("BOM", "finished_product_id", str(product_id))

        # 4. Verificar que todos los materiales existen y son del tipo adecuado
        for item_dto in dto.items:
            material = await self._product_repo.get_by_id(item_dto.material_id)
            if not material:
                raise NotFoundError("Material", str(item_dto.material_id))
            if material.product_type not in (
                ProductType.RAW_MATERIAL,
                ProductType.SUPPLY,
            ):
                raise BusinessRuleViolation(
                    f"El producto '{material.name}' (tipo: {material.product_type}) "
                    f"no puede usarse como material en una receta. "
                    f"Solo se permiten 'raw_material' y 'supply'."
                )

        # 5. Construir entidades de dominio
        now = datetime.now(timezone.utc)
        bom_id = uuid.uuid4()

        items = [
            BOMItem(
                id=uuid.uuid4(),
                bom_id=bom_id,
                material_id=item_dto.material_id,
                quantity_required=item_dto.quantity_required,
                scrap_factor=item_dto.scrap_factor,
                notes=item_dto.notes,
                sort_order=idx,
            )
            for idx, item_dto in enumerate(dto.items)
        ]

        bom = BOM(
            id=bom_id,
            finished_product_id=product_id,
            output_quantity=dto.output_quantity,
            labor_minutes=dto.labor_minutes,
            notes=dto.notes,
            is_active=True,
            created_at=now,
            updated_at=now,
            items=items,
        )

        saved_bom = await self._bom_repo.create_bom(bom)
        _, saved_items = await self._bom_repo.get_bom_with_items(saved_bom.id)

        return BOMDTO.from_domain(saved_bom, saved_items)
```

**Errores posibles:**
- `NotFoundError("Producto", ...)` → HTTP 404
- `NotFoundError("Material", ...)` → HTTP 404
- `BusinessRuleViolation` producto no es `finished_product` → HTTP 422
- `BusinessRuleViolation` material no es `raw_material`/`supply` → HTTP 422
- `AlreadyExistsError` BOM ya existe y está activa → HTTP 409

---

### 8.2 `update_bom.py`

Archivo: `backend/src/application/use_cases/workshop/update_bom.py`

```python
import uuid
from datetime import datetime, timezone

from src.application.dtos.bom_dto import BOMDTO, UpdateBOMDTO
from src.application.exceptions import BusinessRuleViolation, NotFoundError
from src.application.ports.repositories.bom_repository_port import BOMRepositoryPort
from src.application.ports.repositories.product_repository_port import ProductRepositoryPort
from src.domain.models.bom import BOMItem
from src.domain.models.enums import ProductType


class UpdateBOMUseCase:
    """
    Reemplaza completamente la BOM de un producto terminado:
    actualiza cabecera y sustituye todos los items (delete + insert).
    """

    def __init__(
        self,
        bom_repo: BOMRepositoryPort,
        product_repo: ProductRepositoryPort,
    ):
        self._bom_repo = bom_repo
        self._product_repo = product_repo

    async def execute(self, product_id: uuid.UUID, dto: UpdateBOMDTO) -> BOMDTO:
        # 1. Obtener BOM existente
        bom = await self._bom_repo.get_bom_by_product_id(product_id)
        if not bom:
            raise NotFoundError("BOM", f"producto {product_id}")

        # 2. Verificar materiales si se proporcionaron nuevos items
        if dto.items is not None:
            for item_dto in dto.items:
                material = await self._product_repo.get_by_id(item_dto.material_id)
                if not material:
                    raise NotFoundError("Material", str(item_dto.material_id))
                if material.product_type not in (ProductType.RAW_MATERIAL, ProductType.SUPPLY):
                    raise BusinessRuleViolation(
                        f"'{material.name}' (tipo: {material.product_type}) "
                        "no puede usarse como material en una receta."
                    )

        # 3. Actualizar campos de cabecera
        now = datetime.now(timezone.utc)
        if dto.output_quantity is not None:
            bom.output_quantity = dto.output_quantity
        if dto.labor_minutes is not None:
            bom.labor_minutes = dto.labor_minutes
        if dto.notes is not None:
            bom.notes = dto.notes
        if dto.is_active is not None:
            bom.is_active = dto.is_active
        bom.updated_at = now

        updated_bom = await self._bom_repo.update_bom(bom)

        # 4. Reemplazar items si se proporcionaron
        if dto.items is not None:
            _, old_items = await self._bom_repo.get_bom_with_items(bom.id)
            for old_item in old_items:
                await self._bom_repo.remove_bom_item(old_item.id)

            for idx, item_dto in enumerate(dto.items):
                new_item = BOMItem(
                    id=uuid.uuid4(),
                    bom_id=bom.id,
                    material_id=item_dto.material_id,
                    quantity_required=item_dto.quantity_required,
                    scrap_factor=item_dto.scrap_factor,
                    notes=item_dto.notes,
                    sort_order=idx,
                )
                await self._bom_repo.add_bom_item(new_item)

        _, final_items = await self._bom_repo.get_bom_with_items(bom.id)
        return BOMDTO.from_domain(updated_bom, final_items)
```

---

### 8.3 `get_bom.py`

Archivo: `backend/src/application/use_cases/workshop/get_bom.py`

```python
import uuid

from src.application.dtos.bom_dto import BOMWithCostDTO
from src.application.exceptions import NotFoundError
from src.application.ports.repositories.bom_repository_port import BOMRepositoryPort
from src.application.ports.repositories.product_repository_port import ProductRepositoryPort


class GetBOMUseCase:
    def __init__(
        self,
        bom_repo: BOMRepositoryPort,
        product_repo: ProductRepositoryPort,
    ):
        self._bom_repo = bom_repo
        self._product_repo = product_repo

    async def execute(self, product_id: uuid.UUID) -> BOMWithCostDTO:
        bom = await self._bom_repo.get_bom_by_product_id(product_id)
        if not bom:
            raise NotFoundError("BOM", f"producto {product_id}")

        bom, items = await self._bom_repo.get_bom_with_items(bom.id)

        # Construir mapa de precios: usa cost_price si existe, si no base_price
        prices = {}
        material_names = {}
        for item in items:
            material = await self._product_repo.get_by_id(item.material_id)
            if material:
                prices[item.material_id] = material.cost_price or material.base_price
                material_names[item.material_id] = material.name

        bom.items = items
        total_cost = bom.calculate_material_cost(prices) if prices else None
        cost_per_unit = bom.cost_per_unit(prices) if prices else None

        return BOMWithCostDTO.from_domain(
            bom=bom,
            items=items,
            total_cost=total_cost,
            cost_per_unit=cost_per_unit,
            material_names=material_names,
        )
```

---

### 8.4 `calculate_bom_cost.py`

Archivo: `backend/src/application/use_cases/workshop/calculate_bom_cost.py`

```python
import uuid
from decimal import Decimal

from src.application.dtos.bom_dto import BOMCostDetailDTO, BOMCostLineDTO
from src.application.exceptions import NotFoundError
from src.application.ports.repositories.bom_repository_port import BOMRepositoryPort
from src.application.ports.repositories.product_repository_port import ProductRepositoryPort


class CalculateBOMCostUseCase:
    """
    Calcula el costo detallado de una BOM usando precios actuales de los materiales.
    Retorna un desglose línea por línea con subtotales.
    """

    def __init__(self, bom_repo: BOMRepositoryPort, product_repo: ProductRepositoryPort):
        self._bom_repo = bom_repo
        self._product_repo = product_repo

    async def execute(self, product_id: uuid.UUID) -> BOMCostDetailDTO:
        bom = await self._bom_repo.get_bom_by_product_id(product_id)
        if not bom:
            raise NotFoundError("BOM", f"producto {product_id}")

        _, items = await self._bom_repo.get_bom_with_items(bom.id)

        lines: list[BOMCostLineDTO] = []
        total = Decimal("0")

        for item in items:
            material = await self._product_repo.get_by_id(item.material_id)
            if not material:
                raise NotFoundError("Material", str(item.material_id))

            unit_price = material.cost_price or material.base_price
            effective_qty = item.effective_quantity
            subtotal = effective_qty * unit_price
            total += subtotal

            lines.append(BOMCostLineDTO(
                material_id=item.material_id,
                material_name=material.name,
                material_sku=material.sku,
                unit=material.unit,
                quantity_required=item.quantity_required,
                scrap_factor=item.scrap_factor,
                effective_quantity=effective_qty,
                unit_price=unit_price,
                subtotal=subtotal,
            ))

        cost_per_unit = total / bom.output_quantity if bom.output_quantity else Decimal("0")

        return BOMCostDetailDTO(
            bom_id=bom.id,
            finished_product_id=product_id,
            output_quantity=bom.output_quantity,
            lines=lines,
            total_material_cost=total,
            cost_per_unit=cost_per_unit,
            labor_minutes=bom.labor_minutes,
        )
```

---

### 8.5 `list_workshop_products.py`

Archivo: `backend/src/application/use_cases/workshop/list_workshop_products.py`

```python
from uuid import UUID

from src.application.dtos.workshop_dto import WorkshopProductDTO, WorkshopProductListDTO
from src.application.ports.repositories.workshop_product_repository_port import (
    WorkshopProductRepositoryPort,
)
from src.domain.models.enums import ProductType


class ListWorkshopProductsUseCase:
    def __init__(self, workshop_repo: WorkshopProductRepositoryPort):
        self._repo = workshop_repo

    async def execute(
        self,
        product_type: ProductType,
        skip: int = 0,
        limit: int = 50,
        category_id: UUID | None = None,
        search: str | None = None,
        active_only: bool = True,
    ) -> WorkshopProductListDTO:
        if product_type == ProductType.RAW_MATERIAL:
            items = await self._repo.list_raw_materials(
                skip=skip, limit=limit, category_id=category_id,
                search=search, active_only=active_only,
            )
            total = await self._repo.count_raw_materials(
                category_id=category_id, search=search, active_only=active_only,
            )
        elif product_type == ProductType.FINISHED_PRODUCT:
            items = await self._repo.list_finished_products(
                skip=skip, limit=limit, category_id=category_id,
                search=search, active_only=active_only,
            )
            total = await self._repo.count_finished_products(
                category_id=category_id, search=search, active_only=active_only,
            )
        else:
            items = await self._repo.list_by_type(
                product_type=product_type, skip=skip, limit=limit, active_only=active_only,
            )
            total = await self._repo.count_by_type(
                product_type=product_type, active_only=active_only,
            )

        return WorkshopProductListDTO(
            items=[WorkshopProductDTO.from_product(p) for p in items],
            total=total,
            skip=skip,
            limit=limit,
            product_type=product_type,
        )
```

---

## 9. DTOs

### 9.1 BOM DTOs

Archivo: `backend/src/application/dtos/bom_dto.py`

```python
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from src.domain.models.bom import BOM, BOMItem


@dataclass
class BOMItemInputDTO:
    """DTO de entrada para una línea de receta."""
    material_id: UUID
    quantity_required: Decimal
    scrap_factor: Decimal = Decimal("0")
    notes: str | None = None


@dataclass
class CreateBOMDTO:
    output_quantity: Decimal
    items: list[BOMItemInputDTO]
    labor_minutes: int | None = None
    notes: str | None = None


@dataclass
class UpdateBOMDTO:
    output_quantity: Decimal | None = None
    labor_minutes: int | None = None
    notes: str | None = None
    is_active: bool | None = None
    items: list[BOMItemInputDTO] | None = None  # None = no reemplazar items


@dataclass
class BOMItemDTO:
    id: UUID
    bom_id: UUID
    material_id: UUID
    quantity_required: Decimal
    scrap_factor: Decimal
    effective_quantity: Decimal
    sort_order: int
    notes: str | None = None

    @classmethod
    def from_domain(cls, item: BOMItem) -> "BOMItemDTO":
        return cls(
            id=item.id,
            bom_id=item.bom_id,
            material_id=item.material_id,
            quantity_required=item.quantity_required,
            scrap_factor=item.scrap_factor,
            effective_quantity=item.effective_quantity,
            sort_order=item.sort_order,
            notes=item.notes,
        )


@dataclass
class BOMDTO:
    id: UUID
    finished_product_id: UUID
    output_quantity: Decimal
    is_active: bool
    items: list[BOMItemDTO] = field(default_factory=list)
    labor_minutes: int | None = None
    notes: str | None = None

    @classmethod
    def from_domain(cls, bom: BOM, items: list[BOMItem]) -> "BOMDTO":
        return cls(
            id=bom.id,
            finished_product_id=bom.finished_product_id,
            output_quantity=bom.output_quantity,
            is_active=bom.is_active,
            labor_minutes=bom.labor_minutes,
            notes=bom.notes,
            items=[BOMItemDTO.from_domain(i) for i in items],
        )


@dataclass
class BOMWithCostDTO(BOMDTO):
    total_material_cost: Decimal | None = None
    cost_per_unit: Decimal | None = None
    # material_id → nombre del material (enriquecido en use case)
    material_names: dict[UUID, str] = field(default_factory=dict)

    @classmethod
    def from_domain(
        cls,
        bom: BOM,
        items: list[BOMItem],
        total_cost: Decimal | None,
        cost_per_unit: Decimal | None,
        material_names: dict[UUID, str],
    ) -> "BOMWithCostDTO":
        base = BOMDTO.from_domain(bom, items)
        return cls(
            **base.__dict__,
            total_material_cost=total_cost,
            cost_per_unit=cost_per_unit,
            material_names=material_names,
        )


@dataclass
class BOMCostLineDTO:
    material_id: UUID
    material_name: str
    material_sku: str
    unit: str
    quantity_required: Decimal
    scrap_factor: Decimal
    effective_quantity: Decimal
    unit_price: Decimal
    subtotal: Decimal


@dataclass
class BOMCostDetailDTO:
    bom_id: UUID
    finished_product_id: UUID
    output_quantity: Decimal
    lines: list[BOMCostLineDTO]
    total_material_cost: Decimal
    cost_per_unit: Decimal
    labor_minutes: int | None = None
```

### 9.2 Workshop DTOs

Archivo: `backend/src/application/dtos/workshop_dto.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from src.domain.models.enums import ProductType
from src.domain.models.product import Product


@dataclass
class WorkshopProductDTO:
    id: UUID
    sku: str
    name: str
    product_type: str
    category_id: UUID
    base_price: Decimal
    unit: str
    is_active: bool
    show_in_catalog: bool
    cost_price: Decimal | None = None
    wholesale_price: Decimal | None = None
    description: str | None = None
    quantity_on_hand: Decimal | None = None

    @classmethod
    def from_product(cls, p: Product) -> "WorkshopProductDTO":
        return cls(
            id=p.id,
            sku=p.sku,
            name=p.name,
            product_type=p.product_type,
            category_id=p.category_id,
            base_price=p.base_price,
            unit=p.unit,
            is_active=p.is_active,
            show_in_catalog=p.show_in_catalog,
            cost_price=p.cost_price,
            wholesale_price=p.wholesale_price,
            description=p.description,
        )


@dataclass
class WorkshopProductListDTO:
    items: list[WorkshopProductDTO]
    total: int
    skip: int
    limit: int
    product_type: ProductType
```

---

## 10. Schemas de API (Pydantic)

### 10.1 BOM Schemas

Archivo: `backend/src/infrastructure/api/v1/schemas/bom_schema.py`

```python
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class BOMItemCreateRequest(BaseModel):
    material_id: UUID
    quantity_required: Decimal = Field(..., gt=0, description="Cantidad neta requerida")
    scrap_factor: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        le=Decimal("0.9999"),
        description="Factor de desperdicio (0.05 = 5%)",
    )
    notes: str | None = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "material_id": "uuid-del-cuero",
                "quantity_required": "1.500",
                "scrap_factor": "0.05",
                "notes": "Cuero vaqueta 1.5mm espesor",
            }
        }
    }


class BOMCreateRequest(BaseModel):
    output_quantity: Decimal = Field(
        default=Decimal("1"), gt=0,
        description="Unidades de producto terminado que produce esta receta",
    )
    labor_minutes: int | None = Field(None, ge=0, description="Minutos de mano de obra por lote")
    notes: str | None = None
    items: list[BOMItemCreateRequest] = Field(..., min_length=1)

    @field_validator("items")
    @classmethod
    def no_duplicate_materials(cls, items: list[BOMItemCreateRequest]) -> list[BOMItemCreateRequest]:
        ids = [str(i.material_id) for i in items]
        if len(ids) != len(set(ids)):
            raise ValueError("No se puede repetir el mismo material en la receta.")
        return items

    model_config = {
        "json_schema_extra": {
            "example": {
                "output_quantity": "1",
                "labor_minutes": 180,
                "notes": "Receta montura vaquera estándar",
                "items": [
                    {"material_id": "uuid-cuero", "quantity_required": "2.500", "scrap_factor": "0.08"},
                    {"material_id": "uuid-hebilla", "quantity_required": "4", "scrap_factor": "0"},
                    {"material_id": "uuid-hilo", "quantity_required": "0.100", "scrap_factor": "0.02"},
                ],
            }
        }
    }


class BOMUpdateRequest(BaseModel):
    output_quantity: Decimal | None = Field(None, gt=0)
    labor_minutes: int | None = Field(None, ge=0)
    notes: str | None = None
    is_active: bool | None = None
    items: list[BOMItemCreateRequest] | None = None


class BOMItemAddRequest(BaseModel):
    """Para POST /workshop/bom/{product_id}/items — agrega un solo item."""
    material_id: UUID
    quantity_required: Decimal = Field(..., gt=0)
    scrap_factor: Decimal = Field(default=Decimal("0"), ge=0, le=Decimal("0.9999"))
    notes: str | None = None


class BOMItemUpdateRequest(BaseModel):
    """Para PUT /workshop/bom/{product_id}/items/{item_id}."""
    quantity_required: Decimal | None = Field(None, gt=0)
    scrap_factor: Decimal | None = Field(None, ge=0, le=Decimal("0.9999"))
    notes: str | None = None
    sort_order: int | None = Field(None, ge=0)


class BOMItemResponse(BaseModel):
    id: UUID
    bom_id: UUID
    material_id: UUID
    quantity_required: Decimal
    scrap_factor: Decimal
    effective_quantity: Decimal
    sort_order: int
    notes: str | None = None


class BOMResponse(BaseModel):
    id: UUID
    finished_product_id: UUID
    output_quantity: Decimal
    is_active: bool
    labor_minutes: int | None = None
    notes: str | None = None
    items: list[BOMItemResponse] = []


class BOMCostLineResponse(BaseModel):
    material_id: UUID
    material_name: str
    material_sku: str
    unit: str
    quantity_required: Decimal
    scrap_factor: Decimal
    effective_quantity: Decimal
    unit_price: Decimal
    subtotal: Decimal


class BOMWithCostResponse(BOMResponse):
    total_material_cost: Decimal | None = None
    cost_per_unit: Decimal | None = None
    material_names: dict[str, str] = {}  # UUID str → nombre


class BOMCostDetailResponse(BaseModel):
    bom_id: UUID
    finished_product_id: UUID
    output_quantity: Decimal
    lines: list[BOMCostLineResponse]
    total_material_cost: Decimal
    cost_per_unit: Decimal
    labor_minutes: int | None = None
```

### 10.2 Workshop Schemas

Archivo: `backend/src/infrastructure/api/v1/schemas/workshop_schema.py`

```python
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from src.domain.models.enums import ProductType, ProductUnit


class WorkshopProductResponse(BaseModel):
    id: UUID
    sku: str
    name: str
    product_type: str
    category_id: UUID
    base_price: Decimal
    unit: str
    is_active: bool
    show_in_catalog: bool
    cost_price: Decimal | None = None
    wholesale_price: Decimal | None = None
    description: str | None = None
    quantity_on_hand: Decimal | None = None


class WorkshopProductListResponse(BaseModel):
    items: list[WorkshopProductResponse]
    total: int
    skip: int
    limit: int
    product_type: str
```

---

## 11. Endpoints API

Archivo: `backend/src/infrastructure/api/v1/endpoints/workshop.py`

```python
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.application.dtos.bom_dto import (
    BOMItemInputDTO,
    CreateBOMDTO,
    UpdateBOMDTO,
)
from src.application.exceptions import (
    AlreadyExistsError,
    BusinessRuleViolation,
    NotFoundError,
)
from src.application.use_cases.workshop.calculate_bom_cost import CalculateBOMCostUseCase
from src.application.use_cases.workshop.create_bom import CreateBOMUseCase
from src.application.use_cases.workshop.get_bom import GetBOMUseCase
from src.application.use_cases.workshop.list_workshop_products import ListWorkshopProductsUseCase
from src.application.use_cases.workshop.update_bom import UpdateBOMUseCase
from src.dependencies import get_bom_repo, get_product_repo, get_workshop_repo
from src.domain.models.enums import ProductType
from src.infrastructure.api.v1.schemas.bom_schema import (
    BOMCostDetailResponse,
    BOMCreateRequest,
    BOMItemAddRequest,
    BOMItemResponse,
    BOMItemUpdateRequest,
    BOMResponse,
    BOMUpdateRequest,
    BOMWithCostResponse,
)
from src.infrastructure.api.v1.schemas.workshop_schema import (
    WorkshopProductListResponse,
    WorkshopProductResponse,
)

router = APIRouter(prefix="/workshop", tags=["Taller"])


def _not_found(exc: NotFoundError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


def _conflict(exc: AlreadyExistsError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


def _unprocessable(exc: BusinessRuleViolation) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


# ── Materias primas ──────────────────────────────────────────────────────────

@router.get(
    "/materials",
    response_model=WorkshopProductListResponse,
    summary="Listar materias primas",
    description="Retorna productos de tipo `raw_material` con filtros opcionales.",
)
async def list_materials(
    category_id: UUID | None = Query(None, description="Filtrar por categoría"),
    search: str | None = Query(None, description="Búsqueda parcial en nombre o SKU"),
    active_only: bool = Query(True),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    workshop_repo=Depends(get_workshop_repo),
):
    uc = ListWorkshopProductsUseCase(workshop_repo)
    result = await uc.execute(
        product_type=ProductType.RAW_MATERIAL,
        skip=skip, limit=limit,
        category_id=category_id, search=search, active_only=active_only,
    )
    return WorkshopProductListResponse(
        items=[WorkshopProductResponse(**item.__dict__) for item in result.items],
        total=result.total, skip=result.skip, limit=result.limit,
        product_type=result.product_type,
    )


# ── Productos terminados ─────────────────────────────────────────────────────

@router.get(
    "/finished-products",
    response_model=WorkshopProductListResponse,
    summary="Listar productos terminados",
)
async def list_finished_products(
    category_id: UUID | None = Query(None),
    search: str | None = Query(None),
    active_only: bool = Query(True),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    workshop_repo=Depends(get_workshop_repo),
):
    uc = ListWorkshopProductsUseCase(workshop_repo)
    result = await uc.execute(
        product_type=ProductType.FINISHED_PRODUCT,
        skip=skip, limit=limit,
        category_id=category_id, search=search, active_only=active_only,
    )
    return WorkshopProductListResponse(
        items=[WorkshopProductResponse(**item.__dict__) for item in result.items],
        total=result.total, skip=result.skip, limit=result.limit,
        product_type=result.product_type,
    )


# ── BOM ──────────────────────────────────────────────────────────────────────

@router.get(
    "/bom/{product_id}",
    response_model=BOMWithCostResponse,
    summary="Obtener BOM de un producto terminado",
    responses={
        404: {"description": "Producto o BOM no encontrado"},
    },
)
async def get_bom(
    product_id: UUID,
    bom_repo=Depends(get_bom_repo),
    product_repo=Depends(get_product_repo),
):
    uc = GetBOMUseCase(bom_repo, product_repo)
    try:
        dto = await uc.execute(product_id)
    except NotFoundError as exc:
        raise _not_found(exc)

    return BOMWithCostResponse(
        id=dto.id,
        finished_product_id=dto.finished_product_id,
        output_quantity=dto.output_quantity,
        is_active=dto.is_active,
        labor_minutes=dto.labor_minutes,
        notes=dto.notes,
        items=[BOMItemResponse(**item.__dict__) for item in dto.items],
        total_material_cost=dto.total_material_cost,
        cost_per_unit=dto.cost_per_unit,
        material_names={str(k): v for k, v in dto.material_names.items()},
    )


@router.post(
    "/bom/{product_id}",
    response_model=BOMResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear BOM para un producto terminado",
    responses={
        404: {"description": "Producto o material no encontrado"},
        409: {"description": "Ya existe una BOM activa para este producto"},
        422: {"description": "Producto no es finished_product o material no es raw_material/supply"},
    },
)
async def create_bom(
    product_id: UUID,
    body: BOMCreateRequest,
    bom_repo=Depends(get_bom_repo),
    product_repo=Depends(get_product_repo),
):
    uc = CreateBOMUseCase(bom_repo, product_repo)
    dto = CreateBOMDTO(
        output_quantity=body.output_quantity,
        labor_minutes=body.labor_minutes,
        notes=body.notes,
        items=[
            BOMItemInputDTO(
                material_id=i.material_id,
                quantity_required=i.quantity_required,
                scrap_factor=i.scrap_factor,
                notes=i.notes,
            )
            for i in body.items
        ],
    )
    try:
        result = await uc.execute(product_id, dto)
    except NotFoundError as exc:
        raise _not_found(exc)
    except AlreadyExistsError as exc:
        raise _conflict(exc)
    except BusinessRuleViolation as exc:
        raise _unprocessable(exc)

    return BOMResponse(
        id=result.id,
        finished_product_id=result.finished_product_id,
        output_quantity=result.output_quantity,
        is_active=result.is_active,
        labor_minutes=result.labor_minutes,
        notes=result.notes,
        items=[BOMItemResponse(**item.__dict__) for item in result.items],
    )


@router.put(
    "/bom/{product_id}",
    response_model=BOMResponse,
    summary="Reemplazar BOM completo de un producto terminado",
    responses={
        404: {"description": "BOM o material no encontrado"},
        422: {"description": "Material no es raw_material/supply"},
    },
)
async def update_bom(
    product_id: UUID,
    body: BOMUpdateRequest,
    bom_repo=Depends(get_bom_repo),
    product_repo=Depends(get_product_repo),
):
    uc = UpdateBOMUseCase(bom_repo, product_repo)
    dto = UpdateBOMDTO(
        output_quantity=body.output_quantity,
        labor_minutes=body.labor_minutes,
        notes=body.notes,
        is_active=body.is_active,
        items=[
            BOMItemInputDTO(
                material_id=i.material_id,
                quantity_required=i.quantity_required,
                scrap_factor=i.scrap_factor,
                notes=i.notes,
            )
            for i in body.items
        ] if body.items is not None else None,
    )
    try:
        result = await uc.execute(product_id, dto)
    except NotFoundError as exc:
        raise _not_found(exc)
    except BusinessRuleViolation as exc:
        raise _unprocessable(exc)

    return BOMResponse(
        id=result.id,
        finished_product_id=result.finished_product_id,
        output_quantity=result.output_quantity,
        is_active=result.is_active,
        labor_minutes=result.labor_minutes,
        notes=result.notes,
        items=[BOMItemResponse(**item.__dict__) for item in result.items],
    )


@router.post(
    "/bom/{product_id}/items",
    response_model=BOMItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Agregar un material a la receta",
    responses={
        404: {"description": "BOM o material no encontrado"},
        409: {"description": "El material ya existe en esta receta"},
        422: {"description": "Material no es raw_material/supply"},
    },
)
async def add_bom_item(
    product_id: UUID,
    body: BOMItemAddRequest,
    bom_repo=Depends(get_bom_repo),
    product_repo=Depends(get_product_repo),
):
    from src.domain.models.bom import BOMItem
    import uuid as _uuid
    from datetime import datetime, timezone
    from src.domain.models.enums import ProductType as PT

    bom = await bom_repo.get_bom_by_product_id(product_id)
    if not bom:
        raise HTTPException(404, "BOM no encontrada para este producto")

    material = await product_repo.get_by_id(body.material_id)
    if not material:
        raise HTTPException(404, f"Material {body.material_id} no encontrado")
    if material.product_type not in (PT.RAW_MATERIAL, PT.SUPPLY):
        raise HTTPException(422, f"'{material.name}' no puede usarse como material (tipo: {material.product_type})")

    try:
        item = await bom_repo.add_bom_item(BOMItem(
            id=_uuid.uuid4(),
            bom_id=bom.id,
            material_id=body.material_id,
            quantity_required=body.quantity_required,
            scrap_factor=body.scrap_factor,
            notes=body.notes,
            sort_order=0,
        ))
    except AlreadyExistsError as exc:
        raise _conflict(exc)

    return BOMItemResponse(**item.__dict__)


@router.put(
    "/bom/{product_id}/items/{item_id}",
    response_model=BOMItemResponse,
    summary="Editar un item de la receta",
)
async def update_bom_item(
    product_id: UUID,
    item_id: UUID,
    body: BOMItemUpdateRequest,
    bom_repo=Depends(get_bom_repo),
):
    bom, items = await bom_repo.get_bom_with_items(
        (await bom_repo.get_bom_by_product_id(product_id)).id
    ) if await bom_repo.get_bom_by_product_id(product_id) else (None, [])

    if bom is None:
        raise HTTPException(404, "BOM no encontrada")

    existing_item = next((i for i in items if i.id == item_id), None)
    if not existing_item:
        raise HTTPException(404, f"Item {item_id} no encontrado en esta receta")

    if body.quantity_required is not None:
        existing_item.quantity_required = body.quantity_required
    if body.scrap_factor is not None:
        existing_item.scrap_factor = body.scrap_factor
    if body.notes is not None:
        existing_item.notes = body.notes
    if body.sort_order is not None:
        existing_item.sort_order = body.sort_order

    try:
        updated = await bom_repo.update_bom_item(existing_item)
    except NotFoundError as exc:
        raise _not_found(exc)

    return BOMItemResponse(**updated.__dict__)


@router.delete(
    "/bom/{product_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un material de la receta",
)
async def delete_bom_item(
    product_id: UUID,
    item_id: UUID,
    bom_repo=Depends(get_bom_repo),
):
    try:
        await bom_repo.remove_bom_item(item_id)
    except NotFoundError as exc:
        raise _not_found(exc)
```

Registrar el router en `backend/src/infrastructure/api/v1/router.py`:

```python
from src.infrastructure.api.v1.endpoints.workshop import router as workshop_router

api_router.include_router(workshop_router)
```

### Ejemplos de request/response por endpoint

**GET /api/v1/workshop/materials?category_id=uuid&search=cuero&skip=0&limit=20**

Response 200:
```json
{
  "items": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "sku": "CUE-00001",
      "name": "Cuero vaqueta natural 1.5mm",
      "product_type": "raw_material",
      "category_id": "uuid-cueros-pieles",
      "base_price": "850.00",
      "unit": "metro",
      "is_active": true,
      "show_in_catalog": false,
      "cost_price": "820.00",
      "wholesale_price": null,
      "quantity_on_hand": "45.500"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 20,
  "product_type": "raw_material"
}
```

**POST /api/v1/workshop/bom/{product_id}**

Request body:
```json
{
  "output_quantity": "1",
  "labor_minutes": 240,
  "notes": "Montura vaquera cuero de 1ra calidad",
  "items": [
    {
      "material_id": "uuid-cuero-vaqueta",
      "quantity_required": "2.500",
      "scrap_factor": "0.08",
      "notes": "Cuerpo principal y faldones"
    },
    {
      "material_id": "uuid-hebilla-acero",
      "quantity_required": "6",
      "scrap_factor": "0.0000",
      "notes": "Cinchas y estriberas"
    },
    {
      "material_id": "uuid-hilo-cuero",
      "quantity_required": "0.150",
      "scrap_factor": "0.05"
    }
  ]
}
```

Response 201:
```json
{
  "id": "bom-uuid",
  "finished_product_id": "product-uuid",
  "output_quantity": "1.000",
  "is_active": true,
  "labor_minutes": 240,
  "notes": "Montura vaquera cuero de 1ra calidad",
  "items": [
    {
      "id": "item-uuid-1",
      "bom_id": "bom-uuid",
      "material_id": "uuid-cuero-vaqueta",
      "quantity_required": "2.500",
      "scrap_factor": "0.0800",
      "effective_quantity": "2.700",
      "sort_order": 0,
      "notes": "Cuerpo principal y faldones"
    }
  ]
}
```

**GET /api/v1/workshop/bom/{product_id}** — incluye costo calculado

Response 200:
```json
{
  "id": "bom-uuid",
  "finished_product_id": "product-uuid",
  "output_quantity": "1.000",
  "is_active": true,
  "labor_minutes": 240,
  "items": [...],
  "total_material_cost": "2415.75",
  "cost_per_unit": "2415.75",
  "material_names": {
    "uuid-cuero-vaqueta": "Cuero vaqueta natural 1.5mm",
    "uuid-hebilla-acero": "Hebilla acero inoxidable 40mm",
    "uuid-hilo-cuero": "Hilo encerado para cuero"
  }
}
```

**Errores HTTP comunes:**

| Caso | Status | detail |
|------|--------|--------|
| product_id no existe | 404 | "Producto no encontrado: uuid" |
| Producto no es finished_product | 422 | "Solo se puede crear BOM para productos de tipo 'finished_product'..." |
| BOM ya existe y activa | 409 | "BOM ya existe con finished_product_id: 'uuid'" |
| material_id no existe | 404 | "Material no encontrado: uuid" |
| Material no es raw/supply | 422 | "'Montura X' no puede usarse como material..." |
| item_id no pertenece a BOM | 404 | "Item uuid no encontrado en esta receta" |

---

## 12. Cambios en Endpoint de Productos Existente

### 12.1 Schema — agregar campos a `ProductCreateRequest` y `ProductUpdateRequest`

Archivo: `backend/src/infrastructure/api/v1/schemas/product_schema.py`

```python
# Agregar a ProductCreateRequest:
from src.domain.models.enums import ProductType  # nuevo import

product_type: ProductType = ProductType.RESALE
show_in_catalog: bool = False
cost_price: Decimal | None = Field(None, gt=0)

# Agregar a ProductUpdateRequest:
product_type: ProductType | None = None
show_in_catalog: bool | None = None
cost_price: Decimal | None = Field(None, gt=0)

# Agregar a ProductResponse:
product_type: str = "resale"
show_in_catalog: bool = False
cost_price: Decimal | None = None
```

### 12.2 DTO — agregar campos a `CreateProductDTO` y `UpdateProductDTO`

Archivo: `backend/src/application/dtos/product_dto.py`

```python
# En CreateProductDTO:
product_type: "ProductType" = ProductType.RESALE
show_in_catalog: bool = False
cost_price: Decimal | None = None

# En UpdateProductDTO:
product_type: "ProductType | None" = None
show_in_catalog: bool | None = None
cost_price: Decimal | None = None

# En ProductDTO:
product_type: str = "resale"
show_in_catalog: bool = False
cost_price: Decimal | None = None
```

### 12.3 Use case — propagar los campos en `CreateProductUseCase`

En `backend/src/application/use_cases/products/create_product.py`, al construir el objeto `Product`, agregar:

```python
product = Product(
    ...  # campos existentes
    product_type=dto.product_type,
    show_in_catalog=dto.show_in_catalog,
    cost_price=dto.cost_price,
)
```

### 12.4 Filtro adicional en `GET /api/v1/products`

En `backend/src/infrastructure/api/v1/endpoints/products.py`:

```python
@router.get("", response_model=ProductListResponse)
async def list_products(
    active_only: bool = Query(True),
    category_id: UUID | None = Query(None),
    product_type: ProductType | None = Query(None, description="Filtrar por tipo: raw_material, finished_product, resale, etc."),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    ...
):
```

El `ProductRepositoryPort` y su adaptador PostgreSQL deben aceptar el parámetro `product_type: ProductType | None = None` en `list_all()` y `count()`.

### 12.5 SKU prefix — ampliar mapping en `CreateProductUseCase._category_prefix`

```python
CATEGORY_SLUG_PREFIXES = {
    "equino":               "EQU",
    "bovino":               "BOV",
    "accesorios":           "ACC",
    "herreria":             "HER",
    "cueros-pieles":        "CUE",
    "hebilleria-herrajes":  "HEB",
    "coronas-adornos":      "COR",
    "hilos-telas":          "HIL",
    "insumos-taller":       "INS",
    "monturas":             "MON",
    "hakimas-jaquimas":     "JAQ",
    "mantas-sudaderos":     "MAN",
    "riendas-bridas":       "RIE",
    "cincheria":            "CIN",
    "ganaderia":            "GAN",
    "pet-shop":             "PET",
    "herramientas-taller":  "HTA",
}
```

---

## 13. Frontend — Páginas y Componentes

### 13.1 Extensión del formulario de producto (`ProductForm.tsx`)

Archivo: `frontend/src/app/dashboard/productos/ProductForm.tsx`

Agregar al esquema Zod en `frontend/src/schemas/product.schema.ts`:

```typescript
import { z } from "zod";

export const productTypeValues = [
  "raw_material",
  "finished_product",
  "tool",
  "supply",
  "resale",
] as const;
export type ProductType = (typeof productTypeValues)[number];

export const productTypeLabels: Record<ProductType, string> = {
  raw_material:     "Materia Prima",
  finished_product: "Producto Terminado",
  tool:             "Herramienta",
  supply:           "Insumo",
  resale:           "Reventa",
};

// Extender createProductSchema existente:
export const createProductSchema = z.object({
  // ... campos existentes ...
  product_type: z.enum(productTypeValues).default("resale"),
  show_in_catalog: z.boolean().default(false),
  cost_price: z.coerce.number().positive().optional(),
});
```

Cambios en `ProductForm.tsx`:

```tsx
// Agregar después del campo `unit`:
<SelectField
  label="Tipo de producto"
  name="product_type"
  control={control}
  options={productTypeValues.map((v) => ({
    value: v,
    label: productTypeLabels[v],
  }))}
/>

{/* cost_price solo visible para raw_material y supply */}
{(watchProductType === "raw_material" || watchProductType === "supply") && (
  <FormField
    label="Costo de compra (ARS)"
    name="cost_price"
    type="number"
    control={control}
    placeholder="0.00"
  />
)}

{/* show_in_catalog solo para finished_product y resale */}
{(watchProductType === "finished_product" || watchProductType === "resale") && (
  <div className="flex items-center gap-3">
    <input
      type="checkbox"
      id="show_in_catalog"
      {...register("show_in_catalog")}
      className="w-4 h-4 accent-brand-600"
    />
    <label htmlFor="show_in_catalog" className="text-sm text-brand-700">
      Mostrar en catálogo público
    </label>
  </div>
)}
```

El hook `watchProductType` se obtiene con:
```tsx
const watchProductType = watch("product_type");
```

---

### 13.2 Nueva página `/dashboard/taller`

Archivo: `frontend/src/app/dashboard/taller/page.tsx`

**Estructura visual:**

```
┌─────────────────────────────────────────────────────┐
│  🛠 Módulo Taller                                   │
│  Gestión de materias primas y recetas de producción │
├─────────────────────────────────────────────────────┤
│  [Materias Primas]  [Productos Terminados]  ← tabs  │
├─────────────────────────────────────────────────────┤
│  Búsqueda: [____________]  Categoría: [▾]  [+Nuevo] │
├─────────────────────────────────────────────────────┤
│  Tabla con columnas:                                │
│  SKU | Nombre | Categoría | Precio/Costo | Stock   │
│  Para "Productos Terminados": columna extra "Receta"│
│  que muestra botón [Ver/Crear Receta]               │
└─────────────────────────────────────────────────────┘
```

```tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { WorkshopProduct } from "@/types/workshop";
import { workshopService } from "@/services/workshop.service";
import { BOMEditor } from "@/components/workshop/BOMEditor";
import { formatCurrency } from "@/lib/formatters";

type Tab = "materials" | "finished";

export default function TallerPage() {
  const [activeTab, setActiveTab] = useState<Tab>("materials");
  const [search, setSearch] = useState("");
  const [categoryId, setCategoryId] = useState<string | null>(null);
  const [selectedProduct, setSelectedProduct] = useState<WorkshopProduct | null>(null);
  const [showBOMEditor, setShowBOMEditor] = useState(false);
  const router = useRouter();

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-brand-900">Módulo Taller</h1>
        <p className="text-brand-600 text-sm mt-1">
          Gestión de materias primas y recetas de producción
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-brand-200">
        {[
          { id: "materials" as Tab, label: "Materias Primas" },
          { id: "finished" as Tab,  label: "Productos Terminados" },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.id
                ? "border-brand-700 text-brand-900"
                : "border-transparent text-brand-500 hover:text-brand-700"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Filtros */}
      <div className="flex gap-3 items-center">
        <input
          type="text"
          placeholder="Buscar por nombre o SKU..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="border border-brand-300 rounded-md px-3 py-2 text-sm w-64 focus:ring-brand-500"
        />
        {/* CategorySelect — componente a construir con las categorías del backend */}
        <button
          onClick={() => router.push("/dashboard/productos?create=true")}
          className="ml-auto px-4 py-2 bg-brand-700 text-white rounded-md text-sm hover:bg-brand-800"
        >
          + Nuevo producto
        </button>
      </div>

      {/* Contenido según tab */}
      {activeTab === "materials" ? (
        <RawMaterialsTable search={search} categoryId={categoryId} />
      ) : (
        <FinishedProductsTable
          search={search}
          categoryId={categoryId}
          onEditBOM={(product) => {
            setSelectedProduct(product);
            setShowBOMEditor(true);
          }}
        />
      )}

      {/* Modal BOM Editor */}
      {showBOMEditor && selectedProduct && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl w-full max-w-4xl max-h-[90vh] overflow-y-auto">
            <BOMEditor
              product={selectedProduct}
              onClose={() => setShowBOMEditor(false)}
              onSaved={() => setShowBOMEditor(false)}
            />
          </div>
        </div>
      )}
    </div>
  );
}
```

---

### 13.3 Componente `BOMEditor`

Archivo: `frontend/src/components/workshop/BOMEditor.tsx`

**Props:**
```typescript
interface BOMEditorProps {
  product: WorkshopProduct;      // el producto terminado dueño de la receta
  onClose: () => void;
  onSaved: () => void;
}
```

**Estado interno (useState — no Zustand, es formulario efímero):**
```typescript
interface BOMEditorState {
  outputQuantity: number;
  laborMinutes: number | null;
  notes: string;
  items: BOMEditorItem[];
  isLoading: boolean;
  isSaving: boolean;
  error: string | null;
  materialSearch: string;
  materialResults: WorkshopProduct[];
}

interface BOMEditorItem {
  // item de la lista editable en el editor
  materialId: string;
  materialName: string;
  materialSku: string;
  unit: string;
  unitPrice: number;      // cost_price ?? base_price
  quantityRequired: number;
  scrapFactor: number;    // 0–0.9999
  notes: string;
  // calculado
  effectiveQuantity: number;   // quantityRequired × (1 + scrapFactor)
  subtotal: number;            // effectiveQuantity × unitPrice
}
```

**Lógica:**

```tsx
"use client";

import { useEffect, useState } from "react";
import { BOM, BOMItem, WorkshopProduct } from "@/types/workshop";
import { workshopService } from "@/services/workshop.service";
import { formatCurrency } from "@/lib/formatters";

export function BOMEditor({ product, onClose, onSaved }: BOMEditorProps) {
  const [items, setItems] = useState<BOMEditorItem[]>([]);
  const [outputQuantity, setOutputQuantity] = useState(1);
  const [laborMinutes, setLaborMinutes] = useState<number | null>(null);
  const [notes, setNotes] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [existingBomId, setExistingBomId] = useState<string | null>(null);

  // Cargar BOM existente al montar
  useEffect(() => {
    workshopService.getBOM(product.id)
      .then((bom) => {
        setExistingBomId(bom.id);
        setOutputQuantity(bom.output_quantity);
        setLaborMinutes(bom.labor_minutes ?? null);
        setNotes(bom.notes ?? "");
        setItems(bom.items.map(mapBOMItemToEditorItem));
      })
      .catch(() => {
        // No existe BOM aún — editor vacío
      })
      .finally(() => setIsLoading(false));
  }, [product.id]);

  const totalCost = items.reduce((sum, i) => sum + i.subtotal, 0);
  const costPerUnit = outputQuantity > 0 ? totalCost / outputQuantity : 0;

  const handleAddMaterial = (material: WorkshopProduct) => {
    if (items.some((i) => i.materialId === material.id)) return;
    setItems((prev) => [
      ...prev,
      {
        materialId:      material.id,
        materialName:    material.name,
        materialSku:     material.sku,
        unit:            material.unit,
        unitPrice:       material.cost_price ?? material.base_price,
        quantityRequired: 1,
        scrapFactor:     0,
        notes:           "",
        effectiveQuantity: 1,
        subtotal:        material.cost_price ?? material.base_price,
      },
    ]);
  };

  const handleItemChange = (
    index: number,
    field: "quantityRequired" | "scrapFactor" | "notes",
    value: number | string,
  ) => {
    setItems((prev) => {
      const updated = [...prev];
      const item = { ...updated[index], [field]: value };
      item.effectiveQuantity = item.quantityRequired * (1 + item.scrapFactor);
      item.subtotal = item.effectiveQuantity * item.unitPrice;
      updated[index] = item;
      return updated;
    });
  };

  const handleRemoveItem = (index: number) => {
    setItems((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSave = async () => {
    if (items.length === 0) {
      setError("La receta debe tener al menos un material.");
      return;
    }
    setIsSaving(true);
    setError(null);
    try {
      const payload = {
        output_quantity: outputQuantity,
        labor_minutes:   laborMinutes ?? undefined,
        notes:           notes || undefined,
        items: items.map((i) => ({
          material_id:       i.materialId,
          quantity_required: i.quantityRequired,
          scrap_factor:      i.scrapFactor,
          notes:             i.notes || undefined,
        })),
      };

      if (existingBomId) {
        await workshopService.updateBOM(product.id, payload);
      } else {
        await workshopService.createBOM(product.id, payload);
      }
      onSaved();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al guardar la receta.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-start">
        <div>
          <h2 className="text-xl font-bold text-brand-900">
            Receta de producción
          </h2>
          <p className="text-sm text-brand-600">{product.name} ({product.sku})</p>
        </div>
        <button onClick={onClose} className="text-brand-400 hover:text-brand-700 text-2xl leading-none">×</button>
      </div>

      {/* Cabecera BOM */}
      <div className="grid grid-cols-3 gap-4">
        <div>
          <label className="text-xs font-medium text-brand-700">Cantidad producida por lote</label>
          <input
            type="number" min="0.001" step="0.001"
            value={outputQuantity}
            onChange={(e) => setOutputQuantity(parseFloat(e.target.value) || 1)}
            className="mt-1 w-full border border-brand-300 rounded px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="text-xs font-medium text-brand-700">Mano de obra (minutos)</label>
          <input
            type="number" min="0"
            value={laborMinutes ?? ""}
            onChange={(e) => setLaborMinutes(e.target.value ? parseInt(e.target.value) : null)}
            className="mt-1 w-full border border-brand-300 rounded px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="text-xs font-medium text-brand-700">Notas</label>
          <input
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="mt-1 w-full border border-brand-300 rounded px-3 py-2 text-sm"
          />
        </div>
      </div>

      {/* Tabla de materiales */}
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="bg-brand-50 text-brand-700 text-left">
            <th className="px-3 py-2 font-medium">Material</th>
            <th className="px-3 py-2 font-medium">Cantidad</th>
            <th className="px-3 py-2 font-medium">Desperdicio %</th>
            <th className="px-3 py-2 font-medium">Cant. efectiva</th>
            <th className="px-3 py-2 font-medium">Precio unit.</th>
            <th className="px-3 py-2 font-medium">Subtotal</th>
            <th className="px-3 py-2"></th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, idx) => (
            <tr key={item.materialId} className="border-t border-brand-100">
              <td className="px-3 py-2">
                <span className="font-medium">{item.materialName}</span>
                <span className="text-brand-400 text-xs ml-1">{item.materialSku}</span>
              </td>
              <td className="px-3 py-2">
                <input
                  type="number" min="0.001" step="0.001"
                  value={item.quantityRequired}
                  onChange={(e) => handleItemChange(idx, "quantityRequired", parseFloat(e.target.value) || 0)}
                  className="w-20 border border-brand-200 rounded px-2 py-1"
                />
                <span className="text-brand-400 text-xs ml-1">{item.unit}</span>
              </td>
              <td className="px-3 py-2">
                <input
                  type="number" min="0" max="99.99" step="0.01"
                  value={(item.scrapFactor * 100).toFixed(2)}
                  onChange={(e) =>
                    handleItemChange(idx, "scrapFactor", (parseFloat(e.target.value) || 0) / 100)
                  }
                  className="w-20 border border-brand-200 rounded px-2 py-1"
                />
                <span className="text-brand-400 text-xs ml-1">%</span>
              </td>
              <td className="px-3 py-2 text-brand-600">
                {item.effectiveQuantity.toFixed(3)} {item.unit}
              </td>
              <td className="px-3 py-2 text-brand-600">{formatCurrency(item.unitPrice)}</td>
              <td className="px-3 py-2 font-medium text-brand-900">{formatCurrency(item.subtotal)}</td>
              <td className="px-3 py-2">
                <button
                  onClick={() => handleRemoveItem(idx)}
                  className="text-red-400 hover:text-red-600 text-lg leading-none"
                >×</button>
              </td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="border-t-2 border-brand-300 bg-brand-50">
            <td colSpan={5} className="px-3 py-3 text-right font-semibold text-brand-800">
              Costo total del lote:
            </td>
            <td className="px-3 py-3 font-bold text-brand-900 text-lg">
              {formatCurrency(totalCost)}
            </td>
            <td />
          </tr>
          <tr className="bg-brand-50">
            <td colSpan={5} className="px-3 py-2 text-right text-sm text-brand-600">
              Costo por unidad ({outputQuantity} {product.unit}):
            </td>
            <td className="px-3 py-2 font-semibold text-brand-800">
              {formatCurrency(costPerUnit)}
            </td>
            <td />
          </tr>
        </tfoot>
      </table>

      {/* Buscador de materiales */}
      <MaterialSearchPanel onAdd={handleAddMaterial} excludeIds={items.map((i) => i.materialId)} />

      {error && (
        <p className="text-red-600 text-sm bg-red-50 border border-red-200 rounded px-3 py-2">{error}</p>
      )}

      <div className="flex justify-end gap-3 pt-2">
        <button onClick={onClose} className="px-4 py-2 border border-brand-300 text-brand-700 rounded-md text-sm">
          Cancelar
        </button>
        <button
          onClick={handleSave}
          disabled={isSaving}
          className="px-5 py-2 bg-brand-700 text-white rounded-md text-sm hover:bg-brand-800 disabled:opacity-50"
        >
          {isSaving ? "Guardando..." : "Guardar receta"}
        </button>
      </div>
    </div>
  );
}
```

`MaterialSearchPanel` es un sub-componente con un input de búsqueda que llama a `workshopService.listMaterials({ search })` con debounce de 300ms y muestra resultados como botones "Agregar".

---

### 13.4 Nuevos services y types TypeScript

**`frontend/src/types/workshop.ts`**

```typescript
import { ProductUnit } from "./index";

export type ProductType =
  | "raw_material"
  | "finished_product"
  | "tool"
  | "supply"
  | "resale";

export interface WorkshopProduct {
  id: string;
  sku: string;
  name: string;
  product_type: ProductType;
  category_id: string;
  base_price: number;
  unit: ProductUnit;
  is_active: boolean;
  show_in_catalog: boolean;
  cost_price: number | null;
  wholesale_price: number | null;
  description: string | null;
  quantity_on_hand: number | null;
}

export interface WorkshopProductListResponse {
  items: WorkshopProduct[];
  total: number;
  skip: number;
  limit: number;
  product_type: ProductType;
}

export interface BOMItem {
  id: string;
  bom_id: string;
  material_id: string;
  quantity_required: number;
  scrap_factor: number;
  effective_quantity: number;
  sort_order: number;
  notes: string | null;
}

export interface BOM {
  id: string;
  finished_product_id: string;
  output_quantity: number;
  is_active: boolean;
  labor_minutes: number | null;
  notes: string | null;
  items: BOMItem[];
}

export interface BOMWithCost extends BOM {
  total_material_cost: number | null;
  cost_per_unit: number | null;
  material_names: Record<string, string>;
}

export interface BOMCostLine {
  material_id: string;
  material_name: string;
  material_sku: string;
  unit: string;
  quantity_required: number;
  scrap_factor: number;
  effective_quantity: number;
  unit_price: number;
  subtotal: number;
}

export interface BOMCostDetail {
  bom_id: string;
  finished_product_id: string;
  output_quantity: number;
  lines: BOMCostLine[];
  total_material_cost: number;
  cost_per_unit: number;
  labor_minutes: number | null;
}

export interface CreateBOMInput {
  output_quantity: number;
  labor_minutes?: number;
  notes?: string;
  items: {
    material_id: string;
    quantity_required: number;
    scrap_factor?: number;
    notes?: string;
  }[];
}

export interface UpdateBOMInput extends Partial<Omit<CreateBOMInput, "items">> {
  is_active?: boolean;
  items?: CreateBOMInput["items"];
}
```

**`frontend/src/services/workshop.service.ts`**

```typescript
import { api } from "@/lib/api";
import {
  BOMWithCost,
  BOM,
  BOMItem,
  CreateBOMInput,
  UpdateBOMInput,
  WorkshopProduct,
  WorkshopProductListResponse,
} from "@/types/workshop";

interface ListParams {
  skip?: number;
  limit?: number;
  category_id?: string;
  search?: string;
  active_only?: boolean;
}

export const workshopService = {
  async listMaterials(params: ListParams = {}): Promise<WorkshopProductListResponse> {
    const { data } = await api.get<WorkshopProductListResponse>(
      "/workshop/materials",
      { params },
    );
    return data;
  },

  async listFinishedProducts(params: ListParams = {}): Promise<WorkshopProductListResponse> {
    const { data } = await api.get<WorkshopProductListResponse>(
      "/workshop/finished-products",
      { params },
    );
    return data;
  },

  async getBOM(productId: string): Promise<BOMWithCost> {
    const { data } = await api.get<BOMWithCost>(`/workshop/bom/${productId}`);
    return data;
  },

  async createBOM(productId: string, input: CreateBOMInput): Promise<BOM> {
    const { data } = await api.post<BOM>(`/workshop/bom/${productId}`, input);
    return data;
  },

  async updateBOM(productId: string, input: UpdateBOMInput): Promise<BOM> {
    const { data } = await api.put<BOM>(`/workshop/bom/${productId}`, input);
    return data;
  },

  async addBOMItem(
    productId: string,
    item: { material_id: string; quantity_required: number; scrap_factor?: number; notes?: string },
  ): Promise<BOMItem> {
    const { data } = await api.post<BOMItem>(
      `/workshop/bom/${productId}/items`,
      item,
    );
    return data;
  },

  async updateBOMItem(
    productId: string,
    itemId: string,
    patch: { quantity_required?: number; scrap_factor?: number; notes?: string; sort_order?: number },
  ): Promise<BOMItem> {
    const { data } = await api.put<BOMItem>(
      `/workshop/bom/${productId}/items/${itemId}`,
      patch,
    );
    return data;
  },

  async deleteBOMItem(productId: string, itemId: string): Promise<void> {
    await api.delete(`/workshop/bom/${productId}/items/${itemId}`);
  },
};
```

**`frontend/src/schemas/bom.schema.ts`**

```typescript
import { z } from "zod";

export const bomItemSchema = z.object({
  material_id:       z.string().uuid("ID de material inválido"),
  quantity_required: z.coerce.number().positive("La cantidad debe ser mayor a 0"),
  scrap_factor:      z.coerce.number().min(0).max(0.9999).default(0),
  notes:             z.string().optional(),
});

export const createBOMSchema = z.object({
  output_quantity: z.coerce.number().positive("La cantidad producida debe ser mayor a 0").default(1),
  labor_minutes:   z.coerce.number().int().min(0).optional(),
  notes:           z.string().optional(),
  items: z
    .array(bomItemSchema)
    .min(1, "La receta debe tener al menos un material")
    .refine(
      (items) => {
        const ids = items.map((i) => i.material_id);
        return ids.length === new Set(ids).size;
      },
      { message: "No se puede repetir el mismo material en la receta" },
    ),
});

export type CreateBOMValues = z.infer<typeof createBOMSchema>;
export type BOMItemValues  = z.infer<typeof bomItemSchema>;
```

---

## 14. Criterios de Aceptación

- [ ] La migración 002 aplica sin errores sobre una base de datos con datos existentes en las 9 tablas.
- [ ] Todos los productos existentes tienen `product_type = 'resale'`, `show_in_catalog = false`, `cost_price = NULL` después de la migración.
- [ ] Las 13 nuevas categorías aparecen en `GET /api/v1/categories` tras la migración.
- [ ] `POST /api/v1/products` acepta los campos `product_type`, `show_in_catalog` y `cost_price`.
- [ ] `GET /api/v1/products?product_type=raw_material` retorna solo productos de ese tipo.
- [ ] `GET /api/v1/workshop/materials` lista solo productos `raw_material`.
- [ ] `GET /api/v1/workshop/finished-products` lista solo productos `finished_product`.
- [ ] `POST /api/v1/workshop/bom/{id}` con un producto que NO es `finished_product` retorna HTTP 422.
- [ ] `POST /api/v1/workshop/bom/{id}` con un material que NO es `raw_material` ni `supply` retorna HTTP 422.
- [ ] Crear una BOM con 3 items retorna status 201 y los items con `effective_quantity` calculado correctamente.
- [ ] `GET /api/v1/workshop/bom/{id}` retorna `total_material_cost` igual a Σ(qty_efectiva × costo_unitario).
- [ ] Con `scrap_factor = 0.08` y `quantity_required = 2.5`, `effective_quantity` es `2.7` (2.5 × 1.08).
- [ ] `PUT /api/v1/workshop/bom/{id}` con nuevo array de items reemplaza todos los items anteriores.
- [ ] `DELETE /api/v1/workshop/bom/{id}/items/{item_id}` retorna 204 y el item ya no aparece en GET posterior.
- [ ] Intentar crear una segunda BOM activa para el mismo producto retorna HTTP 409.
- [ ] El formulario de producto en el frontend muestra el campo `product_type`.
- [ ] El campo `show_in_catalog` solo es visible cuando `product_type` es `finished_product` o `resale`.
- [ ] El campo `cost_price` solo es visible cuando `product_type` es `raw_material` o `supply`.
- [ ] La página `/dashboard/taller` carga con dos pestañas funcionales.
- [ ] `BOMEditor` carga la BOM existente si el producto ya tiene una.
- [ ] `BOMEditor` calcula y muestra el costo por unidad en tiempo real al editar cantidades.
- [ ] Guardar una receta desde `BOMEditor` llama al endpoint correcto (POST si es nueva, PUT si existe).

---

## 15. Testing

### 15.1 Prueba unitaria — `BOM.calculate_material_cost()`

Archivo: `backend/tests/unit/domain/test_bom.py`

```python
import uuid
from decimal import Decimal
from datetime import datetime, timezone

import pytest

from src.domain.models.bom import BOM, BOMItem


@pytest.fixture
def bom_with_items():
    bom_id = uuid.uuid4()
    mat1 = uuid.uuid4()
    mat2 = uuid.uuid4()
    mat3 = uuid.uuid4()

    items = [
        BOMItem(
            id=uuid.uuid4(), bom_id=bom_id,
            material_id=mat1,
            quantity_required=Decimal("2.500"),
            scrap_factor=Decimal("0.08"),   # → 2.7
        ),
        BOMItem(
            id=uuid.uuid4(), bom_id=bom_id,
            material_id=mat2,
            quantity_required=Decimal("6"),
            scrap_factor=Decimal("0"),      # → 6
        ),
        BOMItem(
            id=uuid.uuid4(), bom_id=bom_id,
            material_id=mat3,
            quantity_required=Decimal("0.150"),
            scrap_factor=Decimal("0.05"),   # → 0.1575
        ),
    ]

    bom = BOM(
        id=bom_id,
        finished_product_id=uuid.uuid4(),
        output_quantity=Decimal("1"),
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        items=items,
    )
    return bom, mat1, mat2, mat3


def test_effective_quantity_with_scrap():
    item = BOMItem(
        id=uuid.uuid4(), bom_id=uuid.uuid4(),
        material_id=uuid.uuid4(),
        quantity_required=Decimal("2.500"),
        scrap_factor=Decimal("0.08"),
    )
    assert item.effective_quantity == Decimal("2.700")


def test_effective_quantity_zero_scrap():
    item = BOMItem(
        id=uuid.uuid4(), bom_id=uuid.uuid4(),
        material_id=uuid.uuid4(),
        quantity_required=Decimal("6"),
        scrap_factor=Decimal("0"),
    )
    assert item.effective_quantity == Decimal("6")


def test_calculate_material_cost(bom_with_items):
    bom, mat1, mat2, mat3 = bom_with_items
    prices = {
        mat1: Decimal("820.00"),   # cuero: 2.7 × 820 = 2214.00
        mat2: Decimal("45.00"),    # hebilla: 6 × 45 = 270.00
        mat3: Decimal("350.00"),   # hilo: 0.1575 × 350 = 55.125
    }
    # Total = 2214.00 + 270.00 + 55.125 = 2539.125
    result = bom.calculate_material_cost(prices)
    assert result == Decimal("2539.125")


def test_cost_per_unit_single_output(bom_with_items):
    bom, mat1, mat2, mat3 = bom_with_items
    prices = {mat1: Decimal("820.00"), mat2: Decimal("45.00"), mat3: Decimal("350.00")}
    assert bom.cost_per_unit(prices) == Decimal("2539.125")


def test_cost_per_unit_batch_of_two(bom_with_items):
    bom, mat1, mat2, mat3 = bom_with_items
    bom.output_quantity = Decimal("2")
    prices = {mat1: Decimal("820.00"), mat2: Decimal("45.00"), mat3: Decimal("350.00")}
    assert bom.cost_per_unit(prices) == Decimal("2539.125") / Decimal("2")


def test_missing_material_raises_key_error(bom_with_items):
    bom, mat1, mat2, _ = bom_with_items
    prices = {mat1: Decimal("820.00"), mat2: Decimal("45.00")}
    # mat3 falta — debe lanzar KeyError
    with pytest.raises(KeyError):
        bom.calculate_material_cost(prices)


def test_calculate_cost_empty_bom():
    bom = BOM(
        id=uuid.uuid4(), finished_product_id=uuid.uuid4(),
        output_quantity=Decimal("1"), is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        items=[],
    )
    assert bom.calculate_material_cost({}) == Decimal("0")
```

### 15.2 Prueba de integración — `CreateBOMUseCase`

Archivo: `backend/tests/integration/use_cases/test_create_bom.py`

```python
import uuid
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.dtos.bom_dto import BOMItemInputDTO, CreateBOMDTO
from src.application.exceptions import AlreadyExistsError, BusinessRuleViolation, NotFoundError
from src.application.use_cases.workshop.create_bom import CreateBOMUseCase
from src.domain.models.bom import BOM, BOMItem
from src.domain.models.enums import ProductType
from src.domain.models.product import Product


def make_product(
    product_type: ProductType = ProductType.FINISHED_PRODUCT,
) -> Product:
    return Product(
        id=uuid.uuid4(), sku="TEST-001", name="Montura test",
        category_id=uuid.uuid4(), base_price=Decimal("50000"),
        unit="unidad", attributes={}, is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        product_type=product_type,
        show_in_catalog=False,
    )


def make_material(product_type: ProductType = ProductType.RAW_MATERIAL) -> Product:
    return Product(
        id=uuid.uuid4(), sku="MAT-001", name="Cuero vaqueta",
        category_id=uuid.uuid4(), base_price=Decimal("820"),
        unit="metro", attributes={}, is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        product_type=product_type,
        show_in_catalog=False,
        cost_price=Decimal("800"),
    )


@pytest.fixture
def setup_mocks():
    bom_repo = MagicMock()
    product_repo = MagicMock()
    bom_repo.get_bom_by_product_id = AsyncMock(return_value=None)
    bom_repo.create_bom = AsyncMock(side_effect=lambda b: b)
    bom_repo.get_bom_with_items = AsyncMock(return_value=(MagicMock(), []))
    return bom_repo, product_repo


@pytest.mark.asyncio
async def test_create_bom_success(setup_mocks):
    bom_repo, product_repo = setup_mocks
    product = make_product(ProductType.FINISHED_PRODUCT)
    material = make_material(ProductType.RAW_MATERIAL)

    product_repo.get_by_id = AsyncMock(side_effect=lambda pid: (
        product if pid == product.id else material
    ))

    uc = CreateBOMUseCase(bom_repo, product_repo)
    dto = CreateBOMDTO(
        output_quantity=Decimal("1"),
        items=[BOMItemInputDTO(
            material_id=material.id,
            quantity_required=Decimal("2.5"),
            scrap_factor=Decimal("0.08"),
        )],
    )
    result = await uc.execute(product.id, dto)
    bom_repo.create_bom.assert_called_once()


@pytest.mark.asyncio
async def test_create_bom_product_not_found(setup_mocks):
    bom_repo, product_repo = setup_mocks
    product_repo.get_by_id = AsyncMock(return_value=None)

    uc = CreateBOMUseCase(bom_repo, product_repo)
    dto = CreateBOMDTO(output_quantity=Decimal("1"), items=[])

    with pytest.raises(NotFoundError):
        await uc.execute(uuid.uuid4(), dto)


@pytest.mark.asyncio
async def test_create_bom_wrong_product_type(setup_mocks):
    bom_repo, product_repo = setup_mocks
    product = make_product(ProductType.RAW_MATERIAL)  # no es finished_product
    product_repo.get_by_id = AsyncMock(return_value=product)

    uc = CreateBOMUseCase(bom_repo, product_repo)
    dto = CreateBOMDTO(output_quantity=Decimal("1"), items=[])

    with pytest.raises(BusinessRuleViolation, match="finished_product"):
        await uc.execute(product.id, dto)


@pytest.mark.asyncio
async def test_create_bom_already_exists(setup_mocks):
    bom_repo, product_repo = setup_mocks
    product = make_product(ProductType.FINISHED_PRODUCT)
    existing_bom = MagicMock()
    existing_bom.is_active = True

    bom_repo.get_bom_by_product_id = AsyncMock(return_value=existing_bom)
    product_repo.get_by_id = AsyncMock(return_value=product)

    uc = CreateBOMUseCase(bom_repo, product_repo)
    dto = CreateBOMDTO(output_quantity=Decimal("1"), items=[])

    with pytest.raises(AlreadyExistsError):
        await uc.execute(product.id, dto)


@pytest.mark.asyncio
async def test_create_bom_material_wrong_type(setup_mocks):
    bom_repo, product_repo = setup_mocks
    product = make_product(ProductType.FINISHED_PRODUCT)
    bad_material = make_material(ProductType.RESALE)  # no puede ser material

    product_repo.get_by_id = AsyncMock(side_effect=lambda pid: (
        product if pid == product.id else bad_material
    ))

    uc = CreateBOMUseCase(bom_repo, product_repo)
    dto = CreateBOMDTO(
        output_quantity=Decimal("1"),
        items=[BOMItemInputDTO(material_id=bad_material.id, quantity_required=Decimal("1"))],
    )

    with pytest.raises(BusinessRuleViolation, match="raw_material"):
        await uc.execute(product.id, dto)
```

### 15.3 Test de la migración — productos existentes conservan `product_type='resale'`

Archivo: `backend/tests/integration/migrations/test_002_migration.py`

```python
"""
Test que verifica que la migración 002 no rompe datos existentes.
Requiere una base de datos de test con la migración 001 aplicada.
"""
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_existing_products_get_default_product_type(db_session: AsyncSession):
    """Todos los productos previos a 002 deben tener product_type='resale'."""
    result = await db_session.execute(
        text("SELECT COUNT(*) FROM products WHERE product_type != 'resale'")
    )
    count = result.scalar()
    assert count == 0, f"Se encontraron {count} productos con product_type distinto de 'resale'"


@pytest.mark.asyncio
async def test_existing_products_show_in_catalog_false(db_session: AsyncSession):
    """show_in_catalog debe ser false para todos los productos previos."""
    result = await db_session.execute(
        text("SELECT COUNT(*) FROM products WHERE show_in_catalog = true")
    )
    count = result.scalar()
    assert count == 0, f"Se encontraron {count} productos con show_in_catalog=true"


@pytest.mark.asyncio
async def test_new_categories_seeded(db_session: AsyncSession):
    """Las 13 nuevas categorías deben existir tras la migración."""
    expected_slugs = [
        "cueros-pieles", "hebilleria-herrajes", "coronas-adornos",
        "hilos-telas", "insumos-taller", "monturas", "hakimas-jaquimas",
        "mantas-sudaderos", "riendas-bridas", "cincheria",
        "ganaderia", "pet-shop", "herramientas-taller",
    ]
    for slug in expected_slugs:
        result = await db_session.execute(
            text("SELECT COUNT(*) FROM categories WHERE slug = :slug"),
            {"slug": slug},
        )
        count = result.scalar()
        assert count == 1, f"Categoría '{slug}' no fue creada por la migración 002"


@pytest.mark.asyncio
async def test_bom_tables_exist(db_session: AsyncSession):
    """Las tablas bom y bom_items deben existir."""
    for table in ("bom", "bom_items"):
        result = await db_session.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_name = :t AND table_schema = 'public'"
            ),
            {"t": table},
        )
        assert result.scalar() == 1, f"La tabla '{table}' no existe"


@pytest.mark.asyncio
async def test_product_new_columns_exist(db_session: AsyncSession):
    """Las columnas product_type, show_in_catalog y cost_price deben existir en products."""
    for col in ("product_type", "show_in_catalog", "cost_price"):
        result = await db_session.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.columns "
                "WHERE table_name = 'products' AND column_name = :c"
            ),
            {"c": col},
        )
        assert result.scalar() == 1, f"La columna 'products.{col}' no existe"
```

---

*Fin de la especificación técnica del Sprint 1.*
