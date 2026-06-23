from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.domain.models.enums import AuditAction


@dataclass
class AuditLog:
    id: UUID
    entity_type: str        # "client", "product", "sale", etc.
    entity_id: UUID
    action: AuditAction
    actor: str              # username o "system"
    created_at: datetime
    payload: dict           # {"before": {...}, "after": {...}}
    ip_address: str | None = None
