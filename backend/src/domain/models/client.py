from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from src.domain.models.enums import ClientType


@dataclass
class Client:
    id: UUID
    full_name: str
    phone: str
    client_type: ClientType
    tags: list[str]
    whatsapp_opt_in: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    email: str | None = None
    address: str | None = None
    notes: str | None = None
    last_purchase_at: datetime | None = None

    def is_wholesale(self) -> bool:
        return self.client_type == ClientType.WHOLESALE

    def add_tag(self, tag: str) -> None:
        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: str) -> None:
        self.tags = [t for t in self.tags if t != tag]

    def has_tag(self, tag: str) -> bool:
        return tag in self.tags
