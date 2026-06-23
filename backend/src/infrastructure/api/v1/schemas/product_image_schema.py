from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ProductImageResponse(BaseModel):
    id: UUID
    product_id: UUID
    url: str
    alt_text: str | None
    sort_order: int
    is_primary: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ReorderImagesRequest(BaseModel):
    ordered_ids: list[UUID] = Field(
        ...,
        min_length=1,
        description="IDs de imágenes en el orden deseado (índice 0 = sort_order 0)",
    )
