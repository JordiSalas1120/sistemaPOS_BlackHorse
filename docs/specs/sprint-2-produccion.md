# Sprint 2 — Flujo de Producción (Órdenes de Taller)

> **Estado**: Especificación lista para implementar  
> **Fecha**: 2026-06-22  
> **Prerrequisito**: Sprint 1 completado (columnas `product_type`, tablas `bom` y `bom_items` presentes)

---

## 1. Objetivo y Alcance

### Objetivo

Implementar el flujo completo de fabricación artesanal: un operario crea una **orden de producción** en el taller, el sistema valida si hay stock suficiente de todos los insumos requeridos por la lista de materiales (BOM), y al completar la orden descuenta automáticamente los materiales consumidos y acredita el producto terminado — todo en una transacción atómica que no puede quedar en estado parcial.

### Alcance del Sprint 2

**Incluido:**
- Tablas `production_orders` y `production_order_items` (migración 003)
- Modelos de dominio: `ProductionOrder`, `ProductionOrderItem`, `ProductionOrderStatus`
- Extensión de `MovementType`: `PRODUCTION_CONSUMPTION` y `PRODUCTION_OUTPUT`
- Servicio de dominio `production_cost_service.py`
- Puerto `ProductionOrderRepositoryPort`
- 5 casos de uso: Create, Start, Complete, Cancel, List
- Adaptador PostgreSQL `ProductionOrderRepository`
- Router `/api/v1/workshop/orders` con 6 endpoints
- Frontend: página `/dashboard/taller/ordenes`, formularios, modal de completar
- Card KPI "Producción" en el dashboard principal

**Excluido (Sprint 3+):**
- Gestión de desperdicios/merma (scrap) configurable por BOM
- Órdenes de producción parciales (entregas múltiples)
- Integración con WhatsApp para notificar al operario
- Planificación de capacidad / calendario de taller

---

## 2. Decisiones de Arquitectura

### 2.1 La transacción de completar orden va en el Use Case, no en el repositorio

El repositorio es responsable de **persistir** una entidad, no de orquestar lógica entre múltiples entidades. `CompleteProductionOrder` involucra:
1. Leer N inventarios (uno por material)
2. Actualizar N inventarios
3. Crear N movimientos de inventario (consumos)
4. Actualizar 1 inventario (producto terminado)
5. Crear 1 movimiento de inventario (salida de producción)
6. Calcular el costo unitario
7. Actualizar el estado de la orden

Esto es orquestación de dominio. El repositorio no debe conocer esta secuencia. El use case recibe todos los repositorios necesarios y los coordina usando **la misma `AsyncSession`** (garantizada por el caching de `Depends` en FastAPI), por lo que el `commit` o `rollback` final cubre todas las operaciones.

### 2.2 Snapshot de precios de costo al crear la orden

El precio de los insumos puede cambiar entre el momento en que se crea la orden y el momento en que se completa. La orden debe reflejar el **costo real de los materiales al momento en que se tomó la decisión de producir** — análogo a cómo `SaleItem.unit_price` congela el precio de venta.

`ProductionOrderItem.unit_cost_snapshot` se carga con `product.base_price` (o `wholesale_price` si aplica) al momento de crear la orden. `unit_cost_snapshot` en `ProductionOrder` se calcula y persiste al completar.

### 2.3 Cómo se extiende MovementType sin romper datos existentes

`MovementType` es un `StrEnum` y la columna en la tabla `inventory_movements` es `VARCHAR(20)`. Para agregar nuevos valores:

1. Agregar las constantes al enum en `domain/models/enums.py`
2. **No se requiere migración de columna** — PostgreSQL acepta cualquier `VARCHAR` nuevo sin `ALTER TYPE` (a diferencia de los tipos `ENUM` nativos de PostgreSQL)
3. Los valores existentes (`sale`, `purchase`, `adjustment`, `return`, `loss`) no se tocan

La migración 003 **no incluye** ningún `ALTER TABLE` sobre `inventory_movements`. Solo agrega las nuevas tablas de producción.

> **Nota**: Si en el futuro se quisiera usar `ENUM` nativo de PostgreSQL para esta columna, se requeriría `ALTER TYPE ... ADD VALUE`. El diseño actual con `VARCHAR` evita esa complejidad.

### 2.4 Numeración ORD-YYYY-NNNNN análoga a VTA-YYYY-NNNNN

Mismo patrón que `SaleRepository.next_sale_number()`:

```python
SELECT COUNT(*) FROM production_orders WHERE EXTRACT(year FROM created_at) = :year
```

Retorna `f"ORD-{year}-{count + 1:05d}"`. El formato garantiza:
- Unicidad de hecho (no se usa para control de concurrencia — en caso extremo de race condition, la constraint `UNIQUE` en la columna lo detectaría)
- Ordenamiento lexicográfico correcto dentro del año
- Legibilidad para el operario

---

## 3. Migración 003 — SQL Completo

Archivo: `backend/alembic/versions/003_production_orders.py`

```python
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
```

---

## 4. Modelos de Dominio

### 4.1 Actualizar enums — `backend/src/domain/models/enums.py`

Agregar a `MovementType`:

```python
class MovementType(StrEnum):
    SALE = "sale"
    PURCHASE = "purchase"
    ADJUSTMENT = "adjustment"
    RETURN = "return"
    LOSS = "loss"
    PRODUCTION_CONSUMPTION = "production_consumption"  # descuento de insumos
    PRODUCTION_OUTPUT = "production_output"             # acreditación del terminado
```

Agregar nuevo enum `ProductionOrderStatus`:

```python
class ProductionOrderStatus(StrEnum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
```

### 4.2 Nuevo archivo `backend/src/domain/models/production_order.py`

```python
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from src.domain.models.enums import ProductionOrderStatus


@dataclass
class ProductionOrderItem:
    id: UUID
    order_id: UUID
    material_id: UUID
    quantity_required: Decimal   # snapshot del BOM al crear la orden
    unit_cost_snapshot: Decimal  # precio del insumo al momento de la orden
    quantity_consumed: Decimal = Decimal("0")   # real al completar
    notes: str | None = None

    @property
    def subtotal_cost(self) -> Decimal:
        """Costo de este ítem usando la cantidad consumida real (o requerida si aún no completó)."""
        qty = self.quantity_consumed if self.quantity_consumed > Decimal("0") else self.quantity_required
        return qty * self.unit_cost_snapshot


@dataclass
class ProductionOrder:
    id: UUID
    order_number: str
    bom_id: UUID
    finished_product_id: UUID
    quantity_to_produce: Decimal
    produced_by: str
    status: ProductionOrderStatus
    created_at: datetime
    updated_at: datetime
    quantity_produced: Decimal = Decimal("0")
    unit_cost_snapshot: Decimal | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None
    notes: str | None = None
    items: list[ProductionOrderItem] = field(default_factory=list)

    # ── Transiciones de estado ────────────────────────────────────────────

    def can_start(self) -> bool:
        """Solo se puede iniciar desde DRAFT."""
        return self.status == ProductionOrderStatus.DRAFT

    def can_complete(self) -> bool:
        """Solo se puede completar desde IN_PROGRESS."""
        return self.status == ProductionOrderStatus.IN_PROGRESS

    def can_cancel(self) -> bool:
        """Se puede cancelar desde DRAFT o IN_PROGRESS. Una orden COMPLETED no se cancela."""
        return self.status in (
            ProductionOrderStatus.DRAFT,
            ProductionOrderStatus.IN_PROGRESS,
        )

    # ── Cálculos de costo ─────────────────────────────────────────────────

    def calculate_total_material_cost(self) -> Decimal:
        """
        Suma (unit_cost_snapshot × quantity_required) para todos los ítems.
        Se usa como estimado antes de completar. Después de completar,
        unit_cost_snapshot en la orden contiene el costo real.
        """
        return sum(
            item.quantity_required * item.unit_cost_snapshot
            for item in self.items
        )

    def calculate_cost_per_unit(self) -> Decimal:
        """
        Costo estimado por unidad del producto terminado.
        Retorna 0 si quantity_to_produce es 0 (evita división por cero).
        """
        if not self.quantity_to_produce:
            return Decimal("0")
        return self.calculate_total_material_cost() / self.quantity_to_produce

    def is_partial_completion(self) -> bool:
        """True si la cantidad producida es menor a la planificada."""
        return self.quantity_produced < self.quantity_to_produce
```

---

## 5. Servicio de Dominio: `production_cost_service.py`

Archivo: `backend/src/domain/services/production_cost_service.py`

```python
"""
Servicio de dominio para el cálculo de costos de producción.
No importa nada de infraestructura ni de aplicación.
"""
from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from src.domain.models.production_order import ProductionOrderItem


@dataclass
class CostItemDetail:
    material_id: UUID
    quantity: Decimal
    unit_price: Decimal
    subtotal: Decimal


@dataclass
class ProductionCostBreakdown:
    material_cost: Decimal
    labor_cost: Decimal
    total_cost: Decimal
    cost_per_unit: Decimal
    quantity_to_produce: Decimal
    items_detail: list[CostItemDetail] = field(default_factory=list)


class ProductionCostService:
    """
    Calcula el costo de producción a partir de los ítems del BOM y,
    opcionalmente, el costo de mano de obra.
    """

    def calculate_production_cost(
        self,
        bom_items: list[ProductionOrderItem],
        material_prices: dict[UUID, Decimal],
        quantity_to_produce: Decimal,
        labor_minutes: int | None = None,
        hourly_rate: Decimal | None = None,
    ) -> ProductionCostBreakdown:
        """
        Calcula el costo de producción completo.

        Args:
            bom_items: Ítems del BOM (o de la orden, con sus snapshots)
            material_prices: Mapa material_id → precio unitario actual
            quantity_to_produce: Unidades a fabricar
            labor_minutes: Minutos de mano de obra por lote (opcional)
            hourly_rate: Tarifa horaria en ARS (opcional)

        Returns:
            ProductionCostBreakdown con el desglose completo.
        """
        items_detail: list[CostItemDetail] = []
        material_cost = Decimal("0")

        for item in bom_items:
            unit_price = material_prices.get(item.material_id, item.unit_cost_snapshot)
            total_qty = item.quantity_required * quantity_to_produce
            subtotal = total_qty * unit_price
            material_cost += subtotal
            items_detail.append(
                CostItemDetail(
                    material_id=item.material_id,
                    quantity=total_qty,
                    unit_price=unit_price,
                    subtotal=subtotal,
                )
            )

        labor_cost = Decimal("0")
        if labor_minutes is not None and hourly_rate is not None and labor_minutes > 0:
            labor_cost = (Decimal(str(labor_minutes)) / Decimal("60")) * hourly_rate

        total_cost = material_cost + labor_cost
        cost_per_unit = (
            total_cost / quantity_to_produce if quantity_to_produce else Decimal("0")
        )

        return ProductionCostBreakdown(
            material_cost=material_cost,
            labor_cost=labor_cost,
            total_cost=total_cost,
            cost_per_unit=cost_per_unit,
            quantity_to_produce=quantity_to_produce,
            items_detail=items_detail,
        )
```

---

## 6. ORM Models

Archivo: `backend/src/infrastructure/database/orm_models/production_order_orm.py`

```python
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.base import Base


class ProductionOrderORM(Base):
    __tablename__ = "production_orders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_number: Mapped[str] = mapped_column(
        String(30), unique=True, nullable=False, index=True
    )
    bom_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bom.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    finished_product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    quantity_to_produce: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    quantity_produced: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), nullable=False, default=Decimal("0")
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft", index=True
    )
    unit_cost_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    produced_by: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    items: Mapped[list["ProductionOrderItemORM"]] = relationship(
        "ProductionOrderItemORM",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="select",
    )
    finished_product: Mapped["ProductORM"] = relationship(  # noqa: F821
        "ProductORM",
        foreign_keys=[finished_product_id],
        lazy="select",
    )


class ProductionOrderItemORM(Base):
    __tablename__ = "production_order_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("production_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    quantity_required: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    quantity_consumed: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), nullable=False, default=Decimal("0")
    )
    unit_cost_snapshot: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    order: Mapped["ProductionOrderORM"] = relationship(
        "ProductionOrderORM", back_populates="items"
    )
    material: Mapped["ProductORM"] = relationship(  # noqa: F821
        "ProductORM",
        foreign_keys=[material_id],
        lazy="select",
    )
```

---

## 7. Puerto: `ProductionOrderRepositoryPort`

Archivo: `backend/src/application/ports/repositories/production_order_repository_port.py`

```python
from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from src.domain.models.enums import ProductionOrderStatus
from src.domain.models.production_order import ProductionOrder, ProductionOrderItem


class ProductionOrderRepositoryPort(ABC):

    @abstractmethod
    async def create_order(
        self,
        order: ProductionOrder,
        items: list[ProductionOrderItem],
    ) -> ProductionOrder:
        """Persiste la orden y sus ítems en una sola operación. Retorna la orden con ítems."""
        ...

    @abstractmethod
    async def get_order(self, order_id: UUID) -> ProductionOrder | None:
        """Retorna la orden sin ítems (cabecera). None si no existe."""
        ...

    @abstractmethod
    async def get_order_with_items(
        self, order_id: UUID
    ) -> tuple[ProductionOrder, list[ProductionOrderItem]] | None:
        """Retorna la orden con sus ítems cargados. None si no existe."""
        ...

    @abstractmethod
    async def list_orders(
        self,
        status: ProductionOrderStatus | None = None,
        finished_product_id: UUID | None = None,
        produced_by: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[ProductionOrder], int]:
        """Retorna (lista de órdenes, total sin paginación)."""
        ...

    @abstractmethod
    async def update_order(self, order: ProductionOrder) -> ProductionOrder:
        """Persiste cambios en la cabecera de la orden (status, timestamps, snapshots)."""
        ...

    @abstractmethod
    async def update_order_items(
        self, items: list[ProductionOrderItem]
    ) -> list[ProductionOrderItem]:
        """Actualiza quantity_consumed en los ítems al completar la orden."""
        ...

    @abstractmethod
    async def next_order_number(self, year: int) -> str:
        """
        Genera el próximo número de orden con formato ORD-YYYY-NNNNN.
        Usa COUNT(*) por año igual que SaleRepository.next_sale_number().
        """
        ...

    @abstractmethod
    async def get_order_items(self, order_id: UUID) -> list[ProductionOrderItem]:
        """Retorna los ítems de una orden. Lista vacía si la orden no existe."""
        ...
```

---

## 8. Use Cases

### 8.1 DTOs previos necesarios

Archivo: `backend/src/application/dtos/production_dto.py` (ver sección 9 completa)

### 8.2 `CreateProductionOrder`

Archivo: `backend/src/application/use_cases/production/create_production_order.py`

```python
import uuid
from datetime import datetime, timezone

from src.application.dtos.production_dto import (
    CreateProductionOrderDTO,
    ProductionOrderDTO,
    ProductionOrderItemDTO,
)
from src.application.exceptions import BusinessRuleViolation, NotFoundError
from src.application.ports.repositories.production_order_repository_port import (
    ProductionOrderRepositoryPort,
)
from src.application.ports.repositories.product_repository_port import ProductRepositoryPort
from src.domain.models.enums import ProductionOrderStatus
from src.domain.models.production_order import ProductionOrder, ProductionOrderItem


class CreateProductionOrderUseCase:
    """
    Crea una orden de producción en estado DRAFT con snapshot de ítems y precios.
    No descuenta stock. No valida disponibilidad (eso es responsabilidad de StartProductionOrder).
    """

    def __init__(
        self,
        order_repo: ProductionOrderRepositoryPort,
        product_repo: ProductRepositoryPort,
        bom_repo,  # BOMRepositoryPort — definido en Sprint 1
    ):
        self._order_repo = order_repo
        self._product_repo = product_repo
        self._bom_repo = bom_repo

    async def execute(self, dto: CreateProductionOrderDTO) -> ProductionOrderDTO:
        # 1. Validar BOM
        bom = await self._bom_repo.get_with_items(dto.bom_id)
        if not bom:
            raise NotFoundError("BOM", str(dto.bom_id))
        if not bom.is_active:
            raise BusinessRuleViolation(
                f"El BOM '{bom.id}' no está activo y no puede usarse para producir."
            )
        if not bom.bom_items:
            raise BusinessRuleViolation(
                "El BOM no tiene ítems de materiales. No se puede crear una orden de producción."
            )

        # 2. Validar producto terminado
        finished_product = await self._product_repo.get_by_id(bom.finished_product_id)
        if not finished_product:
            raise NotFoundError("Producto terminado", str(bom.finished_product_id))
        if not finished_product.is_active:
            raise BusinessRuleViolation(
                f"El producto terminado '{finished_product.name}' no está activo."
            )

        # 3. Construir snapshot de ítems con precios actuales
        now = datetime.now(timezone.utc)
        order_items: list[ProductionOrderItem] = []

        for bom_item in bom.bom_items:
            material = await self._product_repo.get_by_id(bom_item.material_id)
            if not material:
                raise NotFoundError("Material", str(bom_item.material_id))
            if not material.is_active:
                raise BusinessRuleViolation(
                    f"El material '{material.name}' (SKU: {material.sku}) no está activo."
                )

            order_items.append(
                ProductionOrderItem(
                    id=uuid.uuid4(),
                    order_id=uuid.uuid4(),  # placeholder — se reemplaza al crear
                    material_id=bom_item.material_id,
                    quantity_required=bom_item.quantity_per_unit,  # qty por unidad del BOM
                    unit_cost_snapshot=material.base_price,
                    quantity_consumed=0,
                )
            )

        # 4. Generar número de orden
        order_number = await self._order_repo.next_order_number(now.year)
        order_id = uuid.uuid4()

        # Corregir order_id en los ítems
        for item in order_items:
            item.order_id = order_id

        # 5. Construir la orden
        order = ProductionOrder(
            id=order_id,
            order_number=order_number,
            bom_id=dto.bom_id,
            finished_product_id=bom.finished_product_id,
            quantity_to_produce=dto.quantity_to_produce,
            produced_by=dto.produced_by,
            status=ProductionOrderStatus.DRAFT,
            created_at=now,
            updated_at=now,
            notes=dto.notes,
        )

        # 6. Persistir (no descuenta stock)
        saved_order = await self._order_repo.create_order(order, order_items)
        saved_items = await self._order_repo.get_order_items(order_id)

        return _to_dto(saved_order, saved_items)
```

### 8.3 `StartProductionOrder`

Archivo: `backend/src/application/use_cases/production/start_production_order.py`

```python
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from src.application.dtos.production_dto import ProductionOrderDTO
from src.application.exceptions import BusinessRuleViolation, InsufficientStockError, NotFoundError
from src.application.ports.repositories.inventory_repository_port import InventoryRepositoryPort
from src.application.ports.repositories.production_order_repository_port import (
    ProductionOrderRepositoryPort,
)
from src.domain.models.enums import ProductionOrderStatus


class StartProductionOrderUseCase:
    """
    Cambia el estado DRAFT → IN_PROGRESS después de validar que hay stock suficiente
    para todos los materiales requeridos.
    """

    def __init__(
        self,
        order_repo: ProductionOrderRepositoryPort,
        inventory_repo: InventoryRepositoryPort,
    ):
        self._order_repo = order_repo
        self._inventory_repo = inventory_repo

    async def execute(self, order_id: UUID) -> ProductionOrderDTO:
        # 1. Cargar orden con ítems
        result = await self._order_repo.get_order_with_items(order_id)
        if not result:
            raise NotFoundError("Orden de producción", str(order_id))

        order, items = result

        if not order.can_start():
            raise BusinessRuleViolation(
                f"No se puede iniciar una orden en estado '{order.status}'. "
                "Solo las órdenes en estado DRAFT pueden iniciarse."
            )

        # 2. Validar stock de cada material
        # Acumular todos los faltantes antes de lanzar el error (mejor UX)
        shortfalls: list[dict] = []

        for item in items:
            required_total = item.quantity_required * order.quantity_to_produce
            inventory = await self._inventory_repo.get_by_product_id(item.material_id)

            if not inventory:
                shortfalls.append({
                    "material_id": str(item.material_id),
                    "required": float(required_total),
                    "available": 0.0,
                    "missing": float(required_total),
                })
                continue

            if inventory.quantity_on_hand < required_total:
                shortfalls.append({
                    "material_id": str(item.material_id),
                    "required": float(required_total),
                    "available": float(inventory.quantity_on_hand),
                    "missing": float(required_total - inventory.quantity_on_hand),
                })

        if shortfalls:
            # Lanzar con detalle de todos los faltantes
            raise InsufficientStockError(
                product_id=shortfalls[0]["material_id"],
                available=shortfalls[0]["available"],
                requested=shortfalls[0]["required"],
            )
            # Nota: para enviar todos los shortfalls al frontend, se puede subclasificar
            # InsufficientStockError o usar BusinessRuleViolation con payload estructurado.
            # Ver sección 11 para el manejo en el endpoint.

        # 3. Cambiar estado
        now = datetime.now(timezone.utc)
        order.status = ProductionOrderStatus.IN_PROGRESS
        order.started_at = now
        order.updated_at = now

        updated = await self._order_repo.update_order(order)
        items = await self._order_repo.get_order_items(order_id)
        return _to_dto(updated, items)
```

### 8.4 `CompleteProductionOrder`

Archivo: `backend/src/application/use_cases/production/complete_production_order.py`

```python
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from src.application.dtos.production_dto import CompleteProductionOrderDTO, ProductionOrderDTO
from src.application.exceptions import BusinessRuleViolation, InsufficientStockError, NotFoundError
from src.application.ports.repositories.inventory_repository_port import InventoryRepositoryPort
from src.application.ports.repositories.production_order_repository_port import (
    ProductionOrderRepositoryPort,
)
from src.domain.models.enums import MovementType, ProductionOrderStatus
from src.domain.models.inventory import InventoryMovement
from src.domain.services.production_cost_service import ProductionCostService


class CompleteProductionOrderUseCase:
    """
    Transacción atómica:
    1. Descuenta inventario de cada material (PRODUCTION_CONSUMPTION)
    2. Acredita el producto terminado (PRODUCTION_OUTPUT)
    3. Calcula y guarda unit_cost_snapshot
    4. Cambia status a COMPLETED

    Toda la operación comparte la misma AsyncSession (garantizada por FastAPI Depends caching),
    por lo que un error en cualquier paso revierte todo automáticamente.
    """

    def __init__(
        self,
        order_repo: ProductionOrderRepositoryPort,
        inventory_repo: InventoryRepositoryPort,
        cost_service: ProductionCostService,
    ):
        self._order_repo = order_repo
        self._inventory_repo = inventory_repo
        self._cost_service = cost_service

    async def execute(
        self, order_id: UUID, dto: CompleteProductionOrderDTO, actor: str = "system"
    ) -> ProductionOrderDTO:
        # 1. Cargar orden
        result = await self._order_repo.get_order_with_items(order_id)
        if not result:
            raise NotFoundError("Orden de producción", str(order_id))

        order, items = result

        if not order.can_complete():
            raise BusinessRuleViolation(
                f"No se puede completar una orden en estado '{order.status}'. "
                "Solo las órdenes IN_PROGRESS pueden completarse."
            )

        quantity_produced = dto.quantity_produced
        if quantity_produced <= Decimal("0"):
            raise BusinessRuleViolation("La cantidad producida debe ser mayor a 0.")
        if quantity_produced > order.quantity_to_produce:
            raise BusinessRuleViolation(
                f"La cantidad producida ({quantity_produced}) no puede superar "
                f"la planificada ({order.quantity_to_produce})."
            )

        now = datetime.now(timezone.utc)

        # 2. Descontar inventario de materiales (PRODUCTION_CONSUMPTION)
        # Esta parte ocurre dentro de la misma session — si falla aquí, nada persiste.
        for item in items:
            consumed = item.quantity_required * quantity_produced
            inventory = await self._inventory_repo.get_by_product_id(item.material_id)

            if not inventory:
                raise NotFoundError("Inventario de material", str(item.material_id))

            if inventory.quantity_on_hand < consumed:
                raise InsufficientStockError(
                    product_id=str(item.material_id),
                    available=float(inventory.quantity_on_hand),
                    requested=float(consumed),
                )

            qty_before = inventory.quantity_on_hand
            inventory.quantity_on_hand -= consumed
            await self._inventory_repo.update(inventory)

            movement = InventoryMovement(
                id=uuid.uuid4(),
                product_id=item.material_id,
                movement_type=MovementType.PRODUCTION_CONSUMPTION,
                quantity_delta=-consumed,
                quantity_before=qty_before,
                quantity_after=inventory.quantity_on_hand,
                created_by=actor,
                created_at=now,
                reference_id=order_id,
                notes=f"Consumo en orden {order.order_number}",
            )
            await self._inventory_repo.create_movement(movement)

            # Actualizar cantidad consumida real en el ítem
            item.quantity_consumed = consumed

        # 3. Acreditar producto terminado (PRODUCTION_OUTPUT)
        finished_inventory = await self._inventory_repo.get_by_product_id(
            order.finished_product_id
        )
        if not finished_inventory:
            raise NotFoundError("Inventario del producto terminado", str(order.finished_product_id))

        qty_before_finished = finished_inventory.quantity_on_hand
        finished_inventory.quantity_on_hand += quantity_produced
        finished_inventory.last_restocked_at = now
        await self._inventory_repo.update(finished_inventory)

        output_movement = InventoryMovement(
            id=uuid.uuid4(),
            product_id=order.finished_product_id,
            movement_type=MovementType.PRODUCTION_OUTPUT,
            quantity_delta=quantity_produced,
            quantity_before=qty_before_finished,
            quantity_after=finished_inventory.quantity_on_hand,
            created_by=actor,
            created_at=now,
            reference_id=order_id,
            notes=f"Producción completada: {order.order_number}",
        )
        await self._inventory_repo.create_movement(output_movement)

        # 4. Calcular costo unitario real y actualizar ítems
        material_prices = {item.material_id: item.unit_cost_snapshot for item in items}
        cost_breakdown = self._cost_service.calculate_production_cost(
            bom_items=items,
            material_prices=material_prices,
            quantity_to_produce=quantity_produced,
        )

        await self._order_repo.update_order_items(items)

        # 5. Actualizar orden
        order.status = ProductionOrderStatus.COMPLETED
        order.quantity_produced = quantity_produced
        order.completed_at = now
        order.updated_at = now
        order.unit_cost_snapshot = cost_breakdown.cost_per_unit
        if dto.notes:
            order.notes = dto.notes

        updated = await self._order_repo.update_order(order)
        return _to_dto(updated, items)
```

### 8.5 `CancelProductionOrder`

Archivo: `backend/src/application/use_cases/production/cancel_production_order.py`

```python
from datetime import datetime, timezone
from uuid import UUID

from src.application.dtos.production_dto import ProductionOrderDTO
from src.application.exceptions import BusinessRuleViolation, NotFoundError
from src.application.ports.repositories.production_order_repository_port import (
    ProductionOrderRepositoryPort,
)
from src.domain.models.enums import ProductionOrderStatus


class CancelProductionOrderUseCase:
    """
    Cancela una orden en DRAFT o IN_PROGRESS.
    Si estaba IN_PROGRESS, NO revierte stock — el operario debe hacer un ajuste manual
    de inventario si ya había consumido materiales parcialmente.
    """

    def __init__(self, order_repo: ProductionOrderRepositoryPort):
        self._order_repo = order_repo

    async def execute(self, order_id: UUID, reason: str) -> ProductionOrderDTO:
        result = await self._order_repo.get_order_with_items(order_id)
        if not result:
            raise NotFoundError("Orden de producción", str(order_id))

        order, items = result

        if not order.can_cancel():
            raise BusinessRuleViolation(
                f"No se puede cancelar una orden en estado '{order.status}'. "
                "Solo DRAFT e IN_PROGRESS pueden cancelarse."
            )

        now = datetime.now(timezone.utc)
        was_in_progress = order.status == ProductionOrderStatus.IN_PROGRESS

        order.status = ProductionOrderStatus.CANCELLED
        order.cancelled_at = now
        order.updated_at = now
        # Agregar razón a las notas
        cancellation_note = f"[CANCELADO {now.isoformat()}] {reason}"
        if was_in_progress:
            cancellation_note += " — Estaba EN PROGRESO. Verificar stock manualmente."
        order.notes = (
            f"{order.notes}\n{cancellation_note}" if order.notes else cancellation_note
        )

        updated = await self._order_repo.update_order(order)
        return _to_dto(updated, items)
```

### 8.6 `ListProductionOrders`

Archivo: `backend/src/application/use_cases/production/list_production_orders.py`

```python
from datetime import datetime
from uuid import UUID

from src.application.dtos.production_dto import ProductionOrderDTO, ProductionOrderListDTO
from src.application.ports.repositories.production_order_repository_port import (
    ProductionOrderRepositoryPort,
)
from src.domain.models.enums import ProductionOrderStatus


class ListProductionOrdersUseCase:
    def __init__(self, order_repo: ProductionOrderRepositoryPort):
        self._order_repo = order_repo

    async def execute(
        self,
        status: ProductionOrderStatus | None = None,
        finished_product_id: UUID | None = None,
        produced_by: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> ProductionOrderListDTO:
        orders, total = await self._order_repo.list_orders(
            status=status,
            finished_product_id=finished_product_id,
            produced_by=produced_by,
            date_from=date_from,
            date_to=date_to,
            skip=skip,
            limit=limit,
        )
        return ProductionOrderListDTO(
            items=[_to_dto(o, []) for o in orders],
            total=total,
            skip=skip,
            limit=limit,
        )
```

---

## 9. DTOs

Archivo: `backend/src/application/dtos/production_dto.py`

```python
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from src.domain.models.enums import ProductionOrderStatus


# ── Input DTOs ────────────────────────────────────────────────────────────────

@dataclass
class CreateProductionOrderDTO:
    bom_id: UUID
    quantity_to_produce: Decimal
    produced_by: str
    notes: str | None = None


@dataclass
class CompleteProductionOrderDTO:
    quantity_produced: Decimal
    notes: str | None = None


@dataclass
class CancelProductionOrderDTO:
    reason: str


# ── Output DTOs ───────────────────────────────────────────────────────────────

@dataclass
class ProductionOrderItemDTO:
    id: UUID
    order_id: UUID
    material_id: UUID
    material_sku: str
    material_name: str
    quantity_required: Decimal
    quantity_consumed: Decimal
    unit_cost_snapshot: Decimal
    subtotal_cost: Decimal
    notes: str | None = None


@dataclass
class ProductionOrderDTO:
    id: UUID
    order_number: str
    bom_id: UUID
    finished_product_id: UUID
    finished_product_name: str
    finished_product_sku: str
    quantity_to_produce: Decimal
    quantity_produced: Decimal
    status: ProductionOrderStatus
    produced_by: str
    created_at: datetime
    updated_at: datetime
    estimated_cost_per_unit: Decimal
    unit_cost_snapshot: Decimal | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None
    notes: str | None = None
    items: list[ProductionOrderItemDTO] = field(default_factory=list)


@dataclass
class ProductionOrderListDTO:
    items: list[ProductionOrderDTO]
    total: int
    skip: int
    limit: int


# ── Helper de mapeo (compartido entre use cases) ──────────────────────────────

def _to_dto(
    order,
    items: list,
    finished_product_name: str = "",
    finished_product_sku: str = "",
) -> ProductionOrderDTO:
    item_dtos = [
        ProductionOrderItemDTO(
            id=i.id,
            order_id=i.order_id,
            material_id=i.material_id,
            material_sku="",  # se enriquece en el endpoint si se necesita
            material_name="",
            quantity_required=i.quantity_required,
            quantity_consumed=i.quantity_consumed,
            unit_cost_snapshot=i.unit_cost_snapshot,
            subtotal_cost=i.subtotal_cost,
            notes=i.notes,
        )
        for i in items
    ]
    return ProductionOrderDTO(
        id=order.id,
        order_number=order.order_number,
        bom_id=order.bom_id,
        finished_product_id=order.finished_product_id,
        finished_product_name=finished_product_name,
        finished_product_sku=finished_product_sku,
        quantity_to_produce=order.quantity_to_produce,
        quantity_produced=order.quantity_produced,
        status=order.status,
        produced_by=order.produced_by,
        created_at=order.created_at,
        updated_at=order.updated_at,
        estimated_cost_per_unit=order.calculate_cost_per_unit() if order.items else order.unit_cost_snapshot or Decimal("0"),
        unit_cost_snapshot=order.unit_cost_snapshot,
        started_at=order.started_at,
        completed_at=order.completed_at,
        cancelled_at=order.cancelled_at,
        notes=order.notes,
        items=item_dtos,
    )
```

---

## 10. Schemas de API

Archivo: `backend/src/infrastructure/api/v1/schemas/production_schema.py`

```python
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from src.domain.models.enums import ProductionOrderStatus


# ── Request schemas ───────────────────────────────────────────────────────────

class CreateProductionOrderRequest(BaseModel):
    bom_id: UUID
    quantity_to_produce: Decimal = Field(..., gt=0, description="Unidades a fabricar")
    produced_by: str = Field(..., min_length=1, max_length=100, description="Nombre del artífice/operario")
    notes: str | None = Field(None, max_length=1000)

    model_config = {
        "json_schema_extra": {
            "example": {
                "bom_id": "550e8400-e29b-41d4-a716-446655440000",
                "quantity_to_produce": "5",
                "produced_by": "Juan Artesano",
                "notes": "Lote urgente para feria"
            }
        }
    }


class CompleteProductionOrderRequest(BaseModel):
    quantity_produced: Decimal = Field(
        ..., gt=0, description="Cantidad efectivamente producida (puede ser menor a la planificada)"
    )
    notes: str | None = Field(None, max_length=1000, description="Observaciones del completado")

    model_config = {
        "json_schema_extra": {
            "example": {
                "quantity_produced": "5",
                "notes": "Sin inconvenientes"
            }
        }
    }


class CancelProductionOrderRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=500, description="Motivo de la cancelación")

    model_config = {
        "json_schema_extra": {
            "example": {"reason": "Se agotó el cuero antes de iniciar la producción"}
        }
    }


# ── Response schemas ──────────────────────────────────────────────────────────

class ProductionOrderItemResponse(BaseModel):
    id: UUID
    order_id: UUID
    material_id: UUID
    material_sku: str
    material_name: str
    quantity_required: Decimal
    quantity_consumed: Decimal
    unit_cost_snapshot: Decimal
    subtotal_cost: Decimal
    notes: str | None = None


class ProductionOrderResponse(BaseModel):
    id: UUID
    order_number: str
    bom_id: UUID
    finished_product_id: UUID
    finished_product_name: str
    finished_product_sku: str
    quantity_to_produce: Decimal
    quantity_produced: Decimal
    status: ProductionOrderStatus
    produced_by: str
    estimated_cost_per_unit: Decimal
    unit_cost_snapshot: Decimal | None
    started_at: datetime | None
    completed_at: datetime | None
    cancelled_at: datetime | None
    created_at: datetime
    updated_at: datetime
    notes: str | None
    items: list[ProductionOrderItemResponse] = Field(default_factory=list)


class ProductionOrderListResponse(BaseModel):
    items: list[ProductionOrderResponse]
    total: int
    skip: int
    limit: int
```

---

## 11. Endpoints API — Router `/api/v1/workshop/orders`

Archivo: `backend/src/infrastructure/api/v1/endpoints/production_orders.py`

```python
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from src.application.dtos.production_dto import (
    CancelProductionOrderDTO,
    CompleteProductionOrderDTO,
    CreateProductionOrderDTO,
)
from src.application.exceptions import BusinessRuleViolation, InsufficientStockError, NotFoundError
from src.application.ports.repositories.inventory_repository_port import InventoryRepositoryPort
from src.application.ports.repositories.production_order_repository_port import (
    ProductionOrderRepositoryPort,
)
from src.application.ports.repositories.product_repository_port import ProductRepositoryPort
from src.application.use_cases.production.cancel_production_order import CancelProductionOrderUseCase
from src.application.use_cases.production.complete_production_order import CompleteProductionOrderUseCase
from src.application.use_cases.production.create_production_order import CreateProductionOrderUseCase
from src.application.use_cases.production.list_production_orders import ListProductionOrdersUseCase
from src.application.use_cases.production.start_production_order import StartProductionOrderUseCase
from src.dependencies import get_inventory_repo, get_production_order_repo, get_product_repo
from src.domain.models.enums import ProductionOrderStatus
from src.domain.services.production_cost_service import ProductionCostService
from src.infrastructure.api.v1.schemas.production_schema import (
    CancelProductionOrderRequest,
    CompleteProductionOrderRequest,
    CreateProductionOrderRequest,
    ProductionOrderListResponse,
    ProductionOrderResponse,
)

router = APIRouter(prefix="/workshop/orders", tags=["Taller — Órdenes de Producción"])


def _actor(x_actor: str = Header(default="api")) -> str:
    return x_actor


def _order_to_response(dto) -> ProductionOrderResponse:
    items = [
        {
            "id": i.id, "order_id": i.order_id, "material_id": i.material_id,
            "material_sku": i.material_sku, "material_name": i.material_name,
            "quantity_required": i.quantity_required, "quantity_consumed": i.quantity_consumed,
            "unit_cost_snapshot": i.unit_cost_snapshot, "subtotal_cost": i.subtotal_cost,
            "notes": i.notes,
        }
        for i in dto.items
    ]
    return ProductionOrderResponse(**{**dto.__dict__, "items": items})


# GET /workshop/orders
@router.get("", response_model=ProductionOrderListResponse, summary="Listar órdenes de producción")
async def list_orders(
    status: ProductionOrderStatus | None = Query(None, description="Filtrar por estado"),
    finished_product_id: UUID | None = Query(None, description="Filtrar por producto terminado"),
    produced_by: str | None = Query(None, description="Filtrar por artífice"),
    date_from: datetime | None = Query(None, description="Fecha inicio (ISO 8601 UTC)"),
    date_to: datetime | None = Query(None, description="Fecha fin (ISO 8601 UTC)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    order_repo: ProductionOrderRepositoryPort = Depends(get_production_order_repo),
):
    uc = ListProductionOrdersUseCase(order_repo)
    result = await uc.execute(
        status=status, finished_product_id=finished_product_id,
        produced_by=produced_by, date_from=date_from, date_to=date_to,
        skip=skip, limit=limit,
    )
    return ProductionOrderListResponse(
        items=[_order_to_response(o) for o in result.items],
        total=result.total, skip=result.skip, limit=result.limit,
    )


# POST /workshop/orders
@router.post(
    "",
    response_model=ProductionOrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear orden de producción",
)
async def create_order(
    body: CreateProductionOrderRequest,
    actor: str = Depends(_actor),
    order_repo: ProductionOrderRepositoryPort = Depends(get_production_order_repo),
    product_repo: ProductRepositoryPort = Depends(get_product_repo),
    bom_repo=Depends(get_bom_repo),  # agregar factory en dependencies.py
):
    uc = CreateProductionOrderUseCase(order_repo, product_repo, bom_repo)
    try:
        dto = await uc.execute(
            CreateProductionOrderDTO(
                bom_id=body.bom_id,
                quantity_to_produce=body.quantity_to_produce,
                produced_by=body.produced_by,
                notes=body.notes,
            )
        )
        return _order_to_response(dto)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessRuleViolation as e:
        raise HTTPException(status_code=422, detail=str(e))


# GET /workshop/orders/{order_id}
@router.get("/{order_id}", response_model=ProductionOrderResponse, summary="Detalle de orden")
async def get_order(
    order_id: UUID,
    order_repo: ProductionOrderRepositoryPort = Depends(get_production_order_repo),
):
    result = await order_repo.get_order_with_items(order_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Orden {order_id} no encontrada")
    order, items = result
    # Enriquecer con nombres de productos requeriría product_repo — simplificado aquí
    from src.application.dtos.production_dto import _to_dto
    dto = _to_dto(order, items)
    return _order_to_response(dto)


# POST /workshop/orders/{order_id}/start
@router.post(
    "/{order_id}/start",
    response_model=ProductionOrderResponse,
    summary="Iniciar orden (valida stock de materiales)",
)
async def start_order(
    order_id: UUID,
    actor: str = Depends(_actor),
    order_repo: ProductionOrderRepositoryPort = Depends(get_production_order_repo),
    inventory_repo: InventoryRepositoryPort = Depends(get_inventory_repo),
):
    uc = StartProductionOrderUseCase(order_repo, inventory_repo)
    try:
        dto = await uc.execute(order_id)
        return _order_to_response(dto)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InsufficientStockError as e:
        raise HTTPException(
            status_code=409,
            detail={
                "message": str(e),
                "error_code": "INSUFFICIENT_STOCK",
                "product_id": e.product_id,
                "available": e.available,
                "requested": e.requested,
            },
        )
    except BusinessRuleViolation as e:
        raise HTTPException(status_code=422, detail=str(e))


# POST /workshop/orders/{order_id}/complete
@router.post(
    "/{order_id}/complete",
    response_model=ProductionOrderResponse,
    summary="Completar orden (descuenta materiales y acredita terminado — transacción atómica)",
)
async def complete_order(
    order_id: UUID,
    body: CompleteProductionOrderRequest,
    actor: str = Depends(_actor),
    order_repo: ProductionOrderRepositoryPort = Depends(get_production_order_repo),
    inventory_repo: InventoryRepositoryPort = Depends(get_inventory_repo),
):
    uc = CompleteProductionOrderUseCase(
        order_repo, inventory_repo, ProductionCostService()
    )
    try:
        dto = await uc.execute(
            order_id,
            CompleteProductionOrderDTO(
                quantity_produced=body.quantity_produced,
                notes=body.notes,
            ),
            actor=actor,
        )
        return _order_to_response(dto)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InsufficientStockError as e:
        raise HTTPException(
            status_code=409,
            detail={
                "message": str(e),
                "error_code": "INSUFFICIENT_STOCK_AT_COMPLETION",
                "product_id": e.product_id,
                "available": e.available,
                "requested": e.requested,
            },
        )
    except BusinessRuleViolation as e:
        raise HTTPException(status_code=422, detail=str(e))


# POST /workshop/orders/{order_id}/cancel
@router.post(
    "/{order_id}/cancel",
    response_model=ProductionOrderResponse,
    summary="Cancelar orden",
)
async def cancel_order(
    order_id: UUID,
    body: CancelProductionOrderRequest,
    actor: str = Depends(_actor),
    order_repo: ProductionOrderRepositoryPort = Depends(get_production_order_repo),
):
    uc = CancelProductionOrderUseCase(order_repo)
    try:
        dto = await uc.execute(order_id, body.reason)
        return _order_to_response(dto)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessRuleViolation as e:
        raise HTTPException(status_code=422, detail=str(e))
```

### Ejemplos de request/response por endpoint

**POST /workshop/orders** — Crear orden

Request:
```json
{
  "bom_id": "550e8400-e29b-41d4-a716-446655440001",
  "quantity_to_produce": "3",
  "produced_by": "Juan Artesano",
  "notes": "Pedido urgente cliente mayorista"
}
```

Response (201):
```json
{
  "id": "7f3a9c20-1234-4abc-8def-000000000001",
  "order_number": "ORD-2026-00001",
  "bom_id": "550e8400-e29b-41d4-a716-446655440001",
  "finished_product_id": "prod-uuid-001",
  "finished_product_name": "Apero completo vaqueta",
  "finished_product_sku": "APR-001",
  "quantity_to_produce": "3.000",
  "quantity_produced": "0.000",
  "status": "draft",
  "produced_by": "Juan Artesano",
  "estimated_cost_per_unit": "1250.00",
  "unit_cost_snapshot": null,
  "started_at": null,
  "completed_at": null,
  "cancelled_at": null,
  "created_at": "2026-06-22T10:00:00Z",
  "updated_at": "2026-06-22T10:00:00Z",
  "notes": "Pedido urgente cliente mayorista",
  "items": [
    {
      "id": "item-uuid-001",
      "order_id": "7f3a9c20-1234-4abc-8def-000000000001",
      "material_id": "mat-uuid-cuero",
      "material_sku": "CUE-VAQ-01",
      "material_name": "Cuero vaqueta 2mm",
      "quantity_required": "2.500",
      "quantity_consumed": "0.000",
      "unit_cost_snapshot": "350.00",
      "subtotal_cost": "875.00",
      "notes": null
    }
  ]
}
```

**POST /workshop/orders/{id}/start** — Error de stock insuficiente (409):
```json
{
  "detail": {
    "message": "Stock insuficiente para producto mat-uuid-cuero: disponible 4.0, solicitado 7.5",
    "error_code": "INSUFFICIENT_STOCK",
    "product_id": "mat-uuid-cuero",
    "available": 4.0,
    "requested": 7.5
  }
}
```

**POST /workshop/orders/{id}/complete** — Request:
```json
{
  "quantity_produced": "3",
  "notes": "Completado sin inconvenientes"
}
```

Response (200) — status cambia a `completed`, `unit_cost_snapshot` poblado.

**POST /workshop/orders/{id}/cancel** — Request:
```json
{
  "reason": "Se averió la máquina de coser"
}
```

---

## 12. Adaptador PostgreSQL: `ProductionOrderRepository`

Archivo: `backend/src/infrastructure/adapters/postgres_repo/production_order_repository.py`

```python
import uuid
from datetime import datetime
from uuid import UUID

from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.ports.repositories.production_order_repository_port import (
    ProductionOrderRepositoryPort,
)
from src.domain.models.enums import ProductionOrderStatus
from src.domain.models.production_order import ProductionOrder, ProductionOrderItem
from src.infrastructure.database.orm_models.production_order_orm import (
    ProductionOrderItemORM,
    ProductionOrderORM,
)


class ProductionOrderRepository(ProductionOrderRepositoryPort):
    def __init__(self, session: AsyncSession):
        self._session = session

    # ── next_order_number ── mismo patrón que SaleRepository ─────────────────

    async def next_order_number(self, year: int) -> str:
        stmt = select(func.count()).select_from(ProductionOrderORM).where(
            extract("year", ProductionOrderORM.created_at) == year
        )
        result = await self._session.execute(stmt)
        count = result.scalar_one()
        return f"ORD-{year}-{count + 1:05d}"

    # ── create_order ──────────────────────────────────────────────────────────

    async def create_order(
        self,
        order: ProductionOrder,
        items: list[ProductionOrderItem],
    ) -> ProductionOrder:
        orm = ProductionOrderORM(
            id=order.id,
            order_number=order.order_number,
            bom_id=order.bom_id,
            finished_product_id=order.finished_product_id,
            quantity_to_produce=order.quantity_to_produce,
            quantity_produced=order.quantity_produced,
            status=order.status,
            produced_by=order.produced_by,
            notes=order.notes,
            created_at=order.created_at,
            updated_at=order.updated_at,
        )
        self._session.add(orm)
        await self._session.flush()

        for item in items:
            item_orm = ProductionOrderItemORM(
                id=item.id,
                order_id=order.id,
                material_id=item.material_id,
                quantity_required=item.quantity_required,
                quantity_consumed=item.quantity_consumed,
                unit_cost_snapshot=item.unit_cost_snapshot,
                notes=item.notes,
            )
            self._session.add(item_orm)

        await self._session.flush()
        return order

    # ── get_order ─────────────────────────────────────────────────────────────

    async def get_order(self, order_id: UUID) -> ProductionOrder | None:
        stmt = select(ProductionOrderORM).where(ProductionOrderORM.id == order_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def get_order_with_items(
        self, order_id: UUID
    ) -> tuple[ProductionOrder, list[ProductionOrderItem]] | None:
        order = await self.get_order(order_id)
        if not order:
            return None
        items = await self.get_order_items(order_id)
        return order, items

    # ── get_order_items ───────────────────────────────────────────────────────

    async def get_order_items(self, order_id: UUID) -> list[ProductionOrderItem]:
        stmt = select(ProductionOrderItemORM).where(
            ProductionOrderItemORM.order_id == order_id
        )
        result = await self._session.execute(stmt)
        return [self._to_item_domain(r) for r in result.scalars().all()]

    # ── list_orders ───────────────────────────────────────────────────────────

    async def list_orders(
        self,
        status: ProductionOrderStatus | None = None,
        finished_product_id: UUID | None = None,
        produced_by: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[ProductionOrder], int]:
        base_stmt = select(ProductionOrderORM)

        if status:
            base_stmt = base_stmt.where(ProductionOrderORM.status == status)
        if finished_product_id:
            base_stmt = base_stmt.where(
                ProductionOrderORM.finished_product_id == finished_product_id
            )
        if produced_by:
            base_stmt = base_stmt.where(ProductionOrderORM.produced_by == produced_by)
        if date_from:
            base_stmt = base_stmt.where(ProductionOrderORM.created_at >= date_from)
        if date_to:
            base_stmt = base_stmt.where(ProductionOrderORM.created_at <= date_to)

        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar_one()

        paginated = (
            base_stmt.order_by(ProductionOrderORM.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self._session.execute(paginated)
        orders = [self._to_domain(r) for r in result.scalars().all()]
        return orders, total

    # ── update_order ──────────────────────────────────────────────────────────

    async def update_order(self, order: ProductionOrder) -> ProductionOrder:
        orm = await self._session.get(ProductionOrderORM, order.id)
        if not orm:
            return order
        orm.status = order.status
        orm.quantity_produced = order.quantity_produced
        orm.unit_cost_snapshot = order.unit_cost_snapshot
        orm.started_at = order.started_at
        orm.completed_at = order.completed_at
        orm.cancelled_at = order.cancelled_at
        orm.notes = order.notes
        orm.updated_at = order.updated_at
        await self._session.flush()
        return order

    # ── update_order_items ────────────────────────────────────────────────────

    async def update_order_items(
        self, items: list[ProductionOrderItem]
    ) -> list[ProductionOrderItem]:
        for item in items:
            orm = await self._session.get(ProductionOrderItemORM, item.id)
            if orm:
                orm.quantity_consumed = item.quantity_consumed
                orm.notes = item.notes
        await self._session.flush()
        return items

    # ── mappers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _to_domain(orm: ProductionOrderORM) -> ProductionOrder:
        return ProductionOrder(
            id=orm.id,
            order_number=orm.order_number,
            bom_id=orm.bom_id,
            finished_product_id=orm.finished_product_id,
            quantity_to_produce=orm.quantity_to_produce,
            quantity_produced=orm.quantity_produced,
            status=ProductionOrderStatus(orm.status),
            produced_by=orm.produced_by,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            unit_cost_snapshot=orm.unit_cost_snapshot,
            started_at=orm.started_at,
            completed_at=orm.completed_at,
            cancelled_at=orm.cancelled_at,
            notes=orm.notes,
        )

    @staticmethod
    def _to_item_domain(orm: ProductionOrderItemORM) -> ProductionOrderItem:
        return ProductionOrderItem(
            id=orm.id,
            order_id=orm.order_id,
            material_id=orm.material_id,
            quantity_required=orm.quantity_required,
            quantity_consumed=orm.quantity_consumed,
            unit_cost_snapshot=orm.unit_cost_snapshot,
            notes=orm.notes,
        )
```

### Actualizar `dependencies.py`

Agregar al final de `backend/src/dependencies.py`:

```python
from src.infrastructure.adapters.postgres_repo.production_order_repository import (
    ProductionOrderRepository,
)
from src.application.ports.repositories.production_order_repository_port import (
    ProductionOrderRepositoryPort,
)

def get_production_order_repo(
    session: AsyncSession = Depends(get_db_session),
) -> ProductionOrderRepositoryPort:
    return ProductionOrderRepository(session)
```

### Registrar router en `router.py`

En `backend/src/infrastructure/api/v1/router.py`:

```python
from src.infrastructure.api.v1.endpoints.production_orders import router as production_router

api_router.include_router(production_router)
```

---

## 13. Frontend — Páginas y Componentes

### 13.1 Types TypeScript

Archivo: `frontend/src/types/production.ts`

```typescript
// ── Enums ─────────────────────────────────────────────────────────────────────
export type ProductionOrderStatus =
  | "draft"
  | "in_progress"
  | "completed"
  | "cancelled";

export type MovementType =
  | "sale"
  | "purchase"
  | "adjustment"
  | "return"
  | "loss"
  | "production_consumption"
  | "production_output";

// ── Interfaces ────────────────────────────────────────────────────────────────
export interface ProductionOrderItem {
  id: string;
  order_id: string;
  material_id: string;
  material_sku: string;
  material_name: string;
  quantity_required: number;
  quantity_consumed: number;
  unit_cost_snapshot: number;
  subtotal_cost: number;
  notes: string | null;
}

export interface ProductionOrder {
  id: string;
  order_number: string;
  bom_id: string;
  finished_product_id: string;
  finished_product_name: string;
  finished_product_sku: string;
  quantity_to_produce: number;
  quantity_produced: number;
  status: ProductionOrderStatus;
  produced_by: string;
  estimated_cost_per_unit: number;
  unit_cost_snapshot: number | null;
  started_at: string | null;
  completed_at: string | null;
  cancelled_at: string | null;
  created_at: string;
  updated_at: string;
  notes: string | null;
  items: ProductionOrderItem[];
}

export interface ProductionOrderListResponse {
  items: ProductionOrder[];
  total: number;
  skip: number;
  limit: number;
}

// ── Input interfaces ──────────────────────────────────────────────────────────
export interface CreateProductionOrderInput {
  bom_id: string;
  quantity_to_produce: number;
  produced_by: string;
  notes?: string;
}

export interface CompleteProductionOrderInput {
  quantity_produced: number;
  notes?: string;
}

export interface CancelProductionOrderInput {
  reason: string;
}
```

### 13.2 Service

Archivo: `frontend/src/services/workshop.service.ts`

```typescript
import { api } from "@/lib/api";
import type {
  CancelProductionOrderInput,
  CompleteProductionOrderInput,
  CreateProductionOrderInput,
  ProductionOrder,
  ProductionOrderListResponse,
  ProductionOrderStatus,
} from "@/types/production";

export const workshopService = {
  listOrders: async (params?: {
    status?: ProductionOrderStatus;
    finished_product_id?: string;
    produced_by?: string;
    date_from?: string;
    date_to?: string;
    skip?: number;
    limit?: number;
  }): Promise<ProductionOrderListResponse> => {
    const { data } = await api.get<ProductionOrderListResponse>(
      "/workshop/orders",
      { params }
    );
    return data;
  },

  getOrder: async (orderId: string): Promise<ProductionOrder> => {
    const { data } = await api.get<ProductionOrder>(
      `/workshop/orders/${orderId}`
    );
    return data;
  },

  createOrder: async (
    input: CreateProductionOrderInput
  ): Promise<ProductionOrder> => {
    const { data } = await api.post<ProductionOrder>(
      "/workshop/orders",
      input
    );
    return data;
  },

  startOrder: async (orderId: string): Promise<ProductionOrder> => {
    const { data } = await api.post<ProductionOrder>(
      `/workshop/orders/${orderId}/start`
    );
    return data;
  },

  completeOrder: async (
    orderId: string,
    input: CompleteProductionOrderInput
  ): Promise<ProductionOrder> => {
    const { data } = await api.post<ProductionOrder>(
      `/workshop/orders/${orderId}/complete`,
      input
    );
    return data;
  },

  cancelOrder: async (
    orderId: string,
    input: CancelProductionOrderInput
  ): Promise<ProductionOrder> => {
    const { data } = await api.post<ProductionOrder>(
      `/workshop/orders/${orderId}/cancel`,
      input
    );
    return data;
  },

  // Contadores para el dashboard KPI
  getInProgressCount: async (): Promise<number> => {
    const result = await workshopService.listOrders({
      status: "in_progress",
      limit: 1,
    });
    return result.total;
  },

  getCompletedThisMonthCount: async (): Promise<number> => {
    const now = new Date();
    const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
    const result = await workshopService.listOrders({
      status: "completed",
      date_from: firstDay.toISOString(),
      limit: 1,
    });
    return result.total;
  },
};
```

### 13.3 Schemas Zod

Archivo: `frontend/src/schemas/production.schema.ts`

```typescript
import { z } from "zod";

export const createProductionOrderSchema = z.object({
  bom_id: z.string().uuid("Seleccioná un BOM válido"),
  quantity_to_produce: z
    .number({ invalid_type_error: "Ingresá una cantidad" })
    .positive("La cantidad debe ser mayor a 0")
    .max(9999, "Cantidad demasiado grande"),
  produced_by: z
    .string()
    .min(2, "Ingresá el nombre del artífice (mínimo 2 caracteres)")
    .max(100),
  notes: z.string().max(1000).optional(),
});

export const completeProductionOrderSchema = z.object({
  quantity_produced: z
    .number({ invalid_type_error: "Ingresá la cantidad producida" })
    .positive("La cantidad producida debe ser mayor a 0"),
  notes: z.string().max(1000).optional(),
});

export const cancelProductionOrderSchema = z.object({
  reason: z
    .string()
    .min(5, "Ingresá un motivo de al menos 5 caracteres")
    .max(500),
});

export type CreateProductionOrderFormData = z.infer<
  typeof createProductionOrderSchema
>;
export type CompleteProductionOrderFormData = z.infer<
  typeof completeProductionOrderSchema
>;
export type CancelProductionOrderFormData = z.infer<
  typeof cancelProductionOrderSchema
>;
```

### 13.4 Componente `OrderStatusBadge`

Archivo: `frontend/src/components/ui/OrderStatusBadge.tsx`

```tsx
import type { ProductionOrderStatus } from "@/types/production";

const STATUS_CONFIG: Record<
  ProductionOrderStatus,
  { label: string; className: string }
> = {
  draft: {
    label: "Borrador",
    className: "bg-gray-100 text-gray-700 border border-gray-300",
  },
  in_progress: {
    label: "En progreso",
    className: "bg-yellow-100 text-yellow-800 border border-yellow-300",
  },
  completed: {
    label: "Completada",
    className: "bg-green-100 text-green-800 border border-green-300",
  },
  cancelled: {
    label: "Cancelada",
    className: "bg-red-100 text-red-700 border border-red-300",
  },
};

interface OrderStatusBadgeProps {
  status: ProductionOrderStatus;
}

export function OrderStatusBadge({ status }: OrderStatusBadgeProps) {
  const config = STATUS_CONFIG[status];
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.className}`}
    >
      {config.label}
    </span>
  );
}
```

### 13.5 Página `/dashboard/taller/ordenes`

Archivo: `frontend/src/app/dashboard/taller/ordenes/page.tsx`

```tsx
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { workshopService } from "@/services/workshop.service";
import type { ProductionOrder, ProductionOrderStatus } from "@/types/production";
import { OrderStatusBadge } from "@/components/ui/OrderStatusBadge";
import { Button } from "@/components/ui/Button";
import { formatCurrency, formatDate } from "@/lib/formatters";
import { CreateOrderModal } from "./_components/CreateOrderModal";
import { CompleteOrderModal } from "./_components/CompleteOrderModal";
import { CancelOrderModal } from "./_components/CancelOrderModal";

export default function TallerOrdenesPage() {
  const [orders, setOrders] = useState<ProductionOrder[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<
    ProductionOrderStatus | undefined
  >(undefined);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [completeOrder, setCompleteOrder] = useState<ProductionOrder | null>(
    null
  );
  const [cancelOrder, setCancelOrder] = useState<ProductionOrder | null>(null);

  const fetchOrders = async () => {
    setLoading(true);
    try {
      const result = await workshopService.listOrders({
        status: statusFilter,
        limit: 50,
      });
      setOrders(result.items);
      setTotal(result.total);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrders();
  }, [statusFilter]);

  const handleStart = async (orderId: string) => {
    try {
      await workshopService.startOrder(orderId);
      await fetchOrders();
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      if (detail?.error_code === "INSUFFICIENT_STOCK") {
        alert(
          `Stock insuficiente para iniciar la orden.\n` +
            `Material: ${detail.product_id}\n` +
            `Disponible: ${detail.available} — Requerido: ${detail.requested}`
        );
      } else {
        alert(typeof detail === "string" ? detail : "Error al iniciar la orden");
      }
    }
  };

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-brand-900">
            Órdenes de Producción
          </h1>
          <p className="text-sm text-gray-500 mt-1">{total} órdenes en total</p>
        </div>
        <Button onClick={() => setShowCreateModal(true)}>Nueva Orden</Button>
      </div>

      {/* Filtros de estado */}
      <div className="flex gap-2 mb-4 flex-wrap">
        {(
          [
            [undefined, "Todas"],
            ["draft", "Borrador"],
            ["in_progress", "En progreso"],
            ["completed", "Completadas"],
            ["cancelled", "Canceladas"],
          ] as [ProductionOrderStatus | undefined, string][]
        ).map(([val, label]) => (
          <button
            key={label}
            onClick={() => setStatusFilter(val)}
            className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
              statusFilter === val
                ? "bg-brand-700 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Tabla */}
      {loading ? (
        <p className="text-gray-500">Cargando...</p>
      ) : orders.length === 0 ? (
        <p className="text-gray-400 text-center py-12">
          No hay órdenes{statusFilter ? ` en estado "${statusFilter}"` : ""}.
        </p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Número
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Producto
                </th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">
                  Cantidad
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Estado
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Artífice
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Fecha
                </th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">
                  Costo est./u
                </th>
                <th className="px-4 py-3 text-center font-medium text-gray-600">
                  Acciones
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {orders.map((order) => (
                <tr key={order.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono font-medium text-brand-700">
                    <Link
                      href={`/dashboard/taller/ordenes/${order.id}`}
                      className="hover:underline"
                    >
                      {order.order_number}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <div className="font-medium">{order.finished_product_name}</div>
                    <div className="text-xs text-gray-400">
                      {order.finished_product_sku}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right">
                    {order.quantity_produced}/{order.quantity_to_produce}
                  </td>
                  <td className="px-4 py-3">
                    <OrderStatusBadge status={order.status} />
                  </td>
                  <td className="px-4 py-3">{order.produced_by}</td>
                  <td className="px-4 py-3 text-gray-500">
                    {formatDate(order.created_at)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {formatCurrency(order.estimated_cost_per_unit)}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex justify-center gap-1">
                      {order.status === "draft" && (
                        <>
                          <button
                            onClick={() => handleStart(order.id)}
                            className="text-xs px-2 py-1 bg-yellow-100 text-yellow-800 rounded hover:bg-yellow-200"
                          >
                            Iniciar
                          </button>
                          <button
                            onClick={() => setCancelOrder(order)}
                            className="text-xs px-2 py-1 bg-red-50 text-red-700 rounded hover:bg-red-100"
                          >
                            Cancelar
                          </button>
                        </>
                      )}
                      {order.status === "in_progress" && (
                        <>
                          <button
                            onClick={() => setCompleteOrder(order)}
                            className="text-xs px-2 py-1 bg-green-100 text-green-800 rounded hover:bg-green-200"
                          >
                            Completar
                          </button>
                          <button
                            onClick={() => setCancelOrder(order)}
                            className="text-xs px-2 py-1 bg-red-50 text-red-700 rounded hover:bg-red-100"
                          >
                            Cancelar
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Modales */}
      {showCreateModal && (
        <CreateOrderModal
          onClose={() => setShowCreateModal(false)}
          onCreated={fetchOrders}
        />
      )}
      {completeOrder && (
        <CompleteOrderModal
          order={completeOrder}
          onClose={() => setCompleteOrder(null)}
          onCompleted={fetchOrders}
        />
      )}
      {cancelOrder && (
        <CancelOrderModal
          order={cancelOrder}
          onClose={() => setCancelOrder(null)}
          onCancelled={fetchOrders}
        />
      )}
    </div>
  );
}
```

### 13.6 `CompleteOrderModal`

Archivo: `frontend/src/app/dashboard/taller/ordenes/_components/CompleteOrderModal.tsx`

```tsx
"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { workshopService } from "@/services/workshop.service";
import type { ProductionOrder } from "@/types/production";
import {
  completeProductionOrderSchema,
  type CompleteProductionOrderFormData,
} from "@/schemas/production.schema";
import { Modal } from "@/components/ui/Modal";
import { FormField } from "@/components/ui/FormField";
import { Button } from "@/components/ui/Button";
import { formatCurrency } from "@/lib/formatters";

interface CompleteOrderModalProps {
  order: ProductionOrder;
  onClose: () => void;
  onCompleted: () => void;
}

export function CompleteOrderModal({
  order,
  onClose,
  onCompleted,
}: CompleteOrderModalProps) {
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<CompleteProductionOrderFormData>({
    resolver: zodResolver(completeProductionOrderSchema),
    defaultValues: {
      quantity_produced: order.quantity_to_produce,
    },
  });

  const quantityProduced = watch("quantity_produced") || 0;

  const onSubmit = async (data: CompleteProductionOrderFormData) => {
    try {
      await workshopService.completeOrder(order.id, data);
      onCompleted();
      onClose();
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      alert(
        typeof detail === "string"
          ? detail
          : detail?.message || "Error al completar la orden"
      );
    }
  };

  return (
    <Modal title={`Completar ${order.order_number}`} onClose={onClose}>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm">
          <p className="font-medium text-amber-800 mb-1">
            Materiales que se descontarán:
          </p>
          <ul className="space-y-1">
            {order.items.map((item) => {
              const consumed = item.quantity_required * quantityProduced;
              return (
                <li
                  key={item.id}
                  className="flex justify-between text-amber-700"
                >
                  <span>{item.material_name}</span>
                  <span className="font-mono">
                    -{consumed.toFixed(3)} ×{" "}
                    {formatCurrency(item.unit_cost_snapshot)} ={" "}
                    {formatCurrency(consumed * item.unit_cost_snapshot)}
                  </span>
                </li>
              );
            })}
          </ul>
          <p className="mt-2 font-medium text-amber-800 border-t border-amber-200 pt-2">
            Costo total estimado:{" "}
            {formatCurrency(
              order.items.reduce(
                (acc, i) =>
                  acc + i.quantity_required * quantityProduced * i.unit_cost_snapshot,
                0
              )
            )}
          </p>
        </div>

        <FormField
          label="Cantidad producida efectivamente"
          error={errors.quantity_produced?.message}
        >
          <input
            type="number"
            step="0.001"
            min="0.001"
            max={order.quantity_to_produce}
            {...register("quantity_produced", { valueAsNumber: true })}
            className="w-full border rounded-lg px-3 py-2"
          />
          <p className="text-xs text-gray-400 mt-1">
            Planificada: {order.quantity_to_produce}
          </p>
        </FormField>

        <FormField label="Notas (opcional)" error={errors.notes?.message}>
          <textarea
            {...register("notes")}
            rows={2}
            className="w-full border rounded-lg px-3 py-2"
            placeholder="Observaciones del proceso..."
          />
        </FormField>

        <p className="text-xs text-red-600 bg-red-50 border border-red-200 rounded p-2">
          Esta acción es irreversible. Se descontarán los materiales del
          inventario y se acreditará el producto terminado.
        </p>

        <div className="flex justify-end gap-3 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Procesando..." : "Confirmar Completado"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
```

---

## 14. Dashboard KPI — Card "Producción"

En `frontend/src/app/dashboard/page.tsx`, agregar junto a las cards existentes:

```tsx
// En el componente del dashboard, agregar estado:
const [inProgressCount, setInProgressCount] = useState<number>(0);
const [completedThisMonthCount, setCompletedThisMonthCount] = useState<number>(0);

// En el useEffect de carga:
const [inProgress, completedMonth] = await Promise.all([
  workshopService.getInProgressCount(),
  workshopService.getCompletedThisMonthCount(),
]);
setInProgressCount(inProgress);
setCompletedThisMonthCount(completedMonth);
```

Card JSX a insertar en el grid de KPIs:

```tsx
<Link href="/dashboard/taller/ordenes">
  <div className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition-shadow cursor-pointer">
    <div className="flex items-center justify-between mb-3">
      <h3 className="text-sm font-medium text-gray-500">Producción</h3>
      <span className="text-brand-600 text-xl">🔨</span>
    </div>
    <div className="space-y-1">
      <p className="text-2xl font-bold text-brand-900">{inProgressCount}</p>
      <p className="text-xs text-gray-400">órdenes en curso</p>
      <p className="text-sm text-green-600 font-medium mt-2">
        {completedThisMonthCount} completadas este mes
      </p>
    </div>
  </div>
</Link>
```

---

## 15. Criterios de Aceptación

- [ ] **CA-01** — Se puede crear una orden de producción en estado DRAFT asociada a un BOM activo con al menos un ítem.
- [ ] **CA-02** — La orden de producción queda con número en formato `ORD-YYYY-NNNNN`, único e incremental por año.
- [ ] **CA-03** — Al crear la orden, `ProductionOrderItem.unit_cost_snapshot` contiene el precio del material en ese momento (no se actualiza si el precio cambia después).
- [ ] **CA-04** — No se descuenta ningún stock al crear la orden (status DRAFT).
- [ ] **CA-05** — Al intentar iniciar una orden, si algún material no tiene stock suficiente para producir `quantity_to_produce` unidades, el endpoint devuelve HTTP 409 con detalle del material faltante.
- [ ] **CA-06** — Al iniciar exitosamente, el status cambia a IN_PROGRESS y `started_at` queda registrado.
- [ ] **CA-07** — Al completar una orden IN_PROGRESS, el inventario de cada material se descuenta en `quantity_required × quantity_produced`.
- [ ] **CA-08** — Al completar, se crea un `InventoryMovement` de tipo `PRODUCTION_CONSUMPTION` por cada material consumido.
- [ ] **CA-09** — Al completar, el inventario del producto terminado se incrementa en `quantity_produced`.
- [ ] **CA-10** — Al completar, se crea un `InventoryMovement` de tipo `PRODUCTION_OUTPUT` para el producto terminado.
- [ ] **CA-11** — Si falla la acreditación del producto terminado (ej: producto no tiene registro de inventario), los descuentos de materiales se revierten (atomicidad).
- [ ] **CA-12** — Al completar, `unit_cost_snapshot` en la orden se calcula y persiste como costo real por unidad producida.
- [ ] **CA-13** — Se puede completar con `quantity_produced < quantity_to_produce` (producción parcial). Los materiales se descuentan proporcional a lo producido.
- [ ] **CA-14** — Una orden DRAFT puede cancelarse. Una orden IN_PROGRESS puede cancelarse con advertencia de verificar stock.
- [ ] **CA-15** — Una orden COMPLETED no puede cancelarse (devuelve HTTP 422).
- [ ] **CA-16** — La cancelación registra el motivo en `notes` y persiste `cancelled_at`.
- [ ] **CA-17** — El listado de órdenes soporta filtros por `status`, `finished_product_id`, `produced_by`, `date_from`, `date_to` y paginación.
- [ ] **CA-18** — El frontend muestra badge de color correcto por estado: gris (draft), amarillo (in_progress), verde (completed), rojo (cancelled).
- [ ] **CA-19** — El modal de completar muestra en tiempo real el resumen de materiales a descontar con sus costos, actualizándose al cambiar la cantidad producida.
- [ ] **CA-20** — La card KPI del dashboard muestra correctamente las órdenes en curso y las completadas en el mes actual.
- [ ] **CA-21** — `MovementType.PRODUCTION_CONSUMPTION` y `PRODUCTION_OUTPUT` son valores válidos en el enum y no rompen consultas existentes de tipo `SALE`, `PURCHASE`, etc.
- [ ] **CA-22** — `next_order_number` nunca produce duplicados bajo operación normal (el UNIQUE constraint en `order_number` actúa como última línea de defensa).

---

## 16. Testing

### 16.1 Unit tests — `ProductionCostService`

Archivo: `backend/tests/unit/domain/test_production_cost_service.py`

```python
from decimal import Decimal
from uuid import uuid4

import pytest

from src.domain.models.production_order import ProductionOrderItem
from src.domain.services.production_cost_service import ProductionCostService


@pytest.fixture
def service() -> ProductionCostService:
    return ProductionCostService()


@pytest.fixture
def items() -> list[ProductionOrderItem]:
    return [
        ProductionOrderItem(
            id=uuid4(),
            order_id=uuid4(),
            material_id=uuid4(),
            quantity_required=Decimal("2.5"),
            unit_cost_snapshot=Decimal("350.00"),
        ),
        ProductionOrderItem(
            id=uuid4(),
            order_id=uuid4(),
            material_id=uuid4(),
            quantity_required=Decimal("1.0"),
            unit_cost_snapshot=Decimal("120.00"),
        ),
    ]


def test_material_cost_no_labor(service, items):
    """2 ítems, sin mano de obra. Costo = 2.5×350 + 1×120 = 875 + 120 = 995."""
    breakdown = service.calculate_production_cost(
        bom_items=items,
        material_prices={i.material_id: i.unit_cost_snapshot for i in items},
        quantity_to_produce=Decimal("1"),
    )
    assert breakdown.material_cost == Decimal("995.00")
    assert breakdown.labor_cost == Decimal("0")
    assert breakdown.total_cost == Decimal("995.00")
    assert breakdown.cost_per_unit == Decimal("995.00")


def test_cost_scales_with_quantity(service, items):
    """Producir 3 unidades: costo total = 995 × 3 = 2985."""
    breakdown = service.calculate_production_cost(
        bom_items=items,
        material_prices={i.material_id: i.unit_cost_snapshot for i in items},
        quantity_to_produce=Decimal("3"),
    )
    assert breakdown.total_cost == Decimal("2985.00")
    assert breakdown.cost_per_unit == Decimal("995.00")


def test_labor_cost_added(service, items):
    """60 minutos a 600 ARS/hora = 600 ARS de mano de obra."""
    breakdown = service.calculate_production_cost(
        bom_items=items,
        material_prices={i.material_id: i.unit_cost_snapshot for i in items},
        quantity_to_produce=Decimal("1"),
        labor_minutes=60,
        hourly_rate=Decimal("600.00"),
    )
    assert breakdown.labor_cost == Decimal("600.00")
    assert breakdown.total_cost == Decimal("1595.00")


def test_zero_quantity_returns_zero_cost_per_unit(service, items):
    """Evita ZeroDivisionError cuando quantity_to_produce es 0."""
    breakdown = service.calculate_production_cost(
        bom_items=items,
        material_prices={i.material_id: i.unit_cost_snapshot for i in items},
        quantity_to_produce=Decimal("0"),
    )
    assert breakdown.cost_per_unit == Decimal("0")


def test_market_price_overrides_snapshot(service, items):
    """Si se proveen precios actualizados, se usan en lugar del snapshot."""
    updated_prices = {
        items[0].material_id: Decimal("400.00"),  # subió de 350 a 400
        items[1].material_id: Decimal("120.00"),
    }
    breakdown = service.calculate_production_cost(
        bom_items=items,
        material_prices=updated_prices,
        quantity_to_produce=Decimal("1"),
    )
    expected_material = Decimal("2.5") * Decimal("400") + Decimal("1.0") * Decimal("120")
    assert breakdown.material_cost == expected_material
```

### 16.2 Integration test — Atomicidad de `CompleteProductionOrder`

Archivo: `backend/tests/integration/use_cases/test_complete_production_order.py`

```python
"""
Prueba que si la acreditación del producto terminado falla,
los descuentos de materiales se revierten completamente (atomicidad).

Requiere base de datos de test en PostgreSQL.
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dtos.production_dto import CompleteProductionOrderDTO
from src.application.exceptions import NotFoundError
from src.application.use_cases.production.complete_production_order import (
    CompleteProductionOrderUseCase,
)
from src.domain.models.enums import MovementType, ProductionOrderStatus
from src.domain.models.inventory import Inventory
from src.domain.models.production_order import ProductionOrder, ProductionOrderItem
from src.domain.services.production_cost_service import ProductionCostService


@pytest.mark.asyncio
async def test_complete_order_atomicity_rollback(
    db_session: AsyncSession,  # fixture que provee AsyncSession de test con rollback automático
    production_order_factory,  # fixture que crea orden IN_PROGRESS con ítems
    inventory_factory,         # fixture que crea registros de inventario
):
    """
    Escenario: el producto terminado NO tiene registro de inventario.
    Esperado: se lanza NotFoundError y los inventarios de materiales NO se modifican.
    """
    # Setup: materiales con stock suficiente
    material_id = uuid.uuid4()
    material_inventory = await inventory_factory(
        product_id=material_id,
        quantity_on_hand=Decimal("10.0"),
    )
    quantity_before = material_inventory.quantity_on_hand

    # Orden IN_PROGRESS sin inventario del producto terminado
    order = await production_order_factory(
        status=ProductionOrderStatus.IN_PROGRESS,
        quantity_to_produce=Decimal("2"),
        finished_product_id=uuid.uuid4(),  # producto SIN inventario registrado
        items=[
            ProductionOrderItem(
                id=uuid.uuid4(),
                order_id=uuid.uuid4(),  # se reemplaza por factory
                material_id=material_id,
                quantity_required=Decimal("2.0"),
                unit_cost_snapshot=Decimal("100.0"),
            )
        ],
    )

    uc = CompleteProductionOrderUseCase(
        order_repo=...,  # adaptador inicializado con db_session
        inventory_repo=...,
        cost_service=ProductionCostService(),
    )

    with pytest.raises(NotFoundError, match="Inventario del producto terminado"):
        await uc.execute(
            order.id,
            CompleteProductionOrderDTO(quantity_produced=Decimal("2")),
        )

    # Verificar que el inventario del material NO cambió (rollback implícito por la session)
    refreshed = await inventory_repo.get_by_product_id(material_id)
    assert refreshed.quantity_on_hand == quantity_before, (
        "El inventario del material fue modificado a pesar del error — fallo de atomicidad"
    )


@pytest.mark.asyncio
async def test_complete_order_success_movements(
    db_session: AsyncSession,
    production_order_factory,
    inventory_factory,
    inventory_repo,
):
    """Flujo exitoso: verifica movimientos creados y cantidades correctas."""
    material_id = uuid.uuid4()
    finished_id = uuid.uuid4()

    await inventory_factory(product_id=material_id, quantity_on_hand=Decimal("20.0"))
    await inventory_factory(product_id=finished_id, quantity_on_hand=Decimal("0.0"))

    order = await production_order_factory(
        status=ProductionOrderStatus.IN_PROGRESS,
        finished_product_id=finished_id,
        quantity_to_produce=Decimal("3"),
        items=[
            ProductionOrderItem(
                id=uuid.uuid4(),
                order_id=uuid.uuid4(),
                material_id=material_id,
                quantity_required=Decimal("2.0"),
                unit_cost_snapshot=Decimal("100.0"),
            )
        ],
    )

    uc = CompleteProductionOrderUseCase(
        order_repo=..., inventory_repo=inventory_repo, cost_service=ProductionCostService()
    )
    result = await uc.execute(
        order.id, CompleteProductionOrderDTO(quantity_produced=Decimal("3"))
    )

    assert result.status == ProductionOrderStatus.COMPLETED
    assert result.quantity_produced == Decimal("3")
    assert result.unit_cost_snapshot is not None

    # Material descontado: 2.0 × 3 = 6.0 → 20 - 6 = 14
    mat_inv = await inventory_repo.get_by_product_id(material_id)
    assert mat_inv.quantity_on_hand == Decimal("14.0")

    # Terminado acreditado: 0 + 3 = 3
    fin_inv = await inventory_repo.get_by_product_id(finished_id)
    assert fin_inv.quantity_on_hand == Decimal("3.0")
```

### 16.3 Test de `InsufficientStockError` en `StartProductionOrder`

Archivo: `backend/tests/unit/use_cases/test_start_production_order.py`

```python
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.application.exceptions import InsufficientStockError
from src.application.use_cases.production.start_production_order import (
    StartProductionOrderUseCase,
)
from src.domain.models.enums import ProductionOrderStatus
from src.domain.models.inventory import Inventory
from src.domain.models.production_order import ProductionOrder, ProductionOrderItem
from datetime import datetime, timezone


def _make_order(status=ProductionOrderStatus.DRAFT) -> ProductionOrder:
    return ProductionOrder(
        id=uuid4(),
        order_number="ORD-2026-00001",
        bom_id=uuid4(),
        finished_product_id=uuid4(),
        quantity_to_produce=Decimal("5"),
        produced_by="Test",
        status=status,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _make_inventory(product_id, qty: Decimal) -> Inventory:
    return Inventory(
        id=uuid4(),
        product_id=product_id,
        quantity_on_hand=qty,
        low_stock_threshold=Decimal("2"),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_start_raises_when_insufficient_stock():
    material_id = uuid4()
    item = ProductionOrderItem(
        id=uuid4(),
        order_id=uuid4(),
        material_id=material_id,
        quantity_required=Decimal("3.0"),  # 3 × 5 = 15 requeridos
        unit_cost_snapshot=Decimal("100"),
    )
    order = _make_order()

    order_repo = AsyncMock()
    order_repo.get_order_with_items.return_value = (order, [item])

    inventory_repo = AsyncMock()
    # Solo hay 10 en stock, necesita 15
    inventory_repo.get_by_product_id.return_value = _make_inventory(
        material_id, Decimal("10")
    )

    uc = StartProductionOrderUseCase(order_repo, inventory_repo)

    with pytest.raises(InsufficientStockError) as exc_info:
        await uc.execute(order.id)

    assert exc_info.value.product_id == str(material_id)
    assert exc_info.value.available == 10.0
    assert exc_info.value.requested == 15.0


@pytest.mark.asyncio
async def test_start_succeeds_when_stock_exact():
    material_id = uuid4()
    item = ProductionOrderItem(
        id=uuid4(),
        order_id=uuid4(),
        material_id=material_id,
        quantity_required=Decimal("2.0"),  # 2 × 5 = exactamente 10
        unit_cost_snapshot=Decimal("100"),
    )
    order = _make_order()

    order_repo = AsyncMock()
    order_repo.get_order_with_items.return_value = (order, [item])
    order_repo.update_order.return_value = order
    order_repo.get_order_items.return_value = [item]

    inventory_repo = AsyncMock()
    inventory_repo.get_by_product_id.return_value = _make_inventory(
        material_id, Decimal("10")
    )

    uc = StartProductionOrderUseCase(order_repo, inventory_repo)
    result = await uc.execute(order.id)

    assert result is not None
    order_repo.update_order.assert_called_once()
    called_order = order_repo.update_order.call_args[0][0]
    assert called_order.status == ProductionOrderStatus.IN_PROGRESS
    assert called_order.started_at is not None
```

---

*Fin de la especificación técnica del Sprint 2.*
