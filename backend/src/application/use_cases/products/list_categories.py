from src.application.dtos.category_dto import CategoryDTO
from src.application.ports.repositories.category_repository_port import CategoryRepositoryPort


class ListCategoriesUseCase:
    def __init__(self, category_repo: CategoryRepositoryPort):
        self._category_repo = category_repo

    async def execute(self) -> list[CategoryDTO]:
        categories = await self._category_repo.list_all()
        return [
            CategoryDTO(id=c.id, name=c.name, slug=c.slug, description=c.description)
            for c in categories
        ]
