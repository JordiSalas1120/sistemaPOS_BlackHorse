from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from src.domain.models.enums import ClientType


class ClientCreateRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=200)
    phone: str = Field(..., min_length=7, max_length=30)
    client_type: ClientType = ClientType.RETAIL
    email: EmailStr | None = None
    address: str | None = None
    notes: str | None = None
    whatsapp_opt_in: bool = False
    tags: list[str] = Field(default_factory=list)

    model_config = {
        "json_schema_extra": {
            "example": {
                "full_name": "Juan Pérez",
                "phone": "+5491155552222",
                "client_type": "retail",
                "email": "juan@example.com",
                "whatsapp_opt_in": True,
            }
        }
    }


class ClientUpdateRequest(BaseModel):
    full_name: str | None = Field(None, min_length=1, max_length=200)
    phone: str | None = Field(None, min_length=7, max_length=30)
    email: EmailStr | None = None
    address: str | None = None
    notes: str | None = None
    client_type: ClientType | None = None
    whatsapp_opt_in: bool | None = None
    is_active: bool | None = None


class TagRequest(BaseModel):
    tag: str = Field(..., min_length=1, max_length=50)


class ClientResponse(BaseModel):
    id: UUID
    full_name: str
    phone: str
    email: str | None = None
    address: str | None = None
    client_type: str
    tags: list[str]
    notes: str | None = None
    whatsapp_opt_in: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_purchase_at: datetime | None = None


class ClientListResponse(BaseModel):
    items: list[ClientResponse]
    total: int
    skip: int
    limit: int
