from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from src.domain.models.enums import ClientType


@dataclass
class CreateClientDTO:
    full_name: str
    phone: str
    client_type: ClientType = ClientType.RETAIL
    email: str | None = None
    address: str | None = None
    notes: str | None = None
    whatsapp_opt_in: bool = False
    tags: list[str] = field(default_factory=list)


@dataclass
class UpdateClientDTO:
    full_name: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    notes: str | None = None
    client_type: ClientType | None = None
    whatsapp_opt_in: bool | None = None
    is_active: bool | None = None


@dataclass
class ClientDTO:
    id: UUID
    full_name: str
    phone: str
    client_type: str
    tags: list[str]
    whatsapp_opt_in: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    email: str | None = None
    address: str | None = None
    notes: str | None = None
    last_purchase_at: datetime | None = None


@dataclass
class ClientListDTO:
    items: list[ClientDTO]
    total: int
    skip: int
    limit: int
