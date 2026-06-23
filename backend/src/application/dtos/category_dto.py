from dataclasses import dataclass
from uuid import UUID


@dataclass
class CreateCategoryDTO:
    name: str
    slug: str
    description: str | None = None


@dataclass
class CategoryDTO:
    id: UUID
    name: str
    slug: str
    description: str | None
