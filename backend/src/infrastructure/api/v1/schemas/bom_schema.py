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
