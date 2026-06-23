import uuid
from datetime import datetime, timezone

from src.application.dtos.category_dto import CategoryDTO, CreateCategoryDTO
from src.application.exceptions import AlreadyExistsError
from src.application.ports.repositories.category_repository_port import CategoryRepositoryPort
from src.domain.models.product import Category


class CreateCategoryUseCase:
    def __init__(self, category_repo: CategoryRepositoryPort):
        self._category_repo = category_repo

    async def execute(self, dto: CreateCategoryDTO) -> CategoryDTO:
        existing = await self._category_repo.get_by_slug(dto.slug)
        if existing:
            raise AlreadyExistsError("Categoría", "slug", dto.slug)

        category = Category(
            id=uuid.uuid4(),
            name=dto.name,
            slug=dto.slug,
            description=dto.description,
            created_at=datetime.now(timezone.utc),
        )
        saved = await self._category_repo.create(category)
        return CategoryDTO(id=saved.id, name=saved.name, slug=saved.slug, description=saved.description)
