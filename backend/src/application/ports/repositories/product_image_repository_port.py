from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.models.catalog import ProductImage


class ProductImageRepositoryPort(ABC):
    """Puerto para gestión de imágenes de producto (operaciones admin)."""

    @abstractmethod
    async def get_images_for_product(self, product_id: UUID) -> list[ProductImage]:
        ...

    @abstractmethod
    async def add_image(self, image: ProductImage) -> ProductImage:
        ...

    @abstractmethod
    async def set_primary_image(self, product_id: UUID, image_id: UUID) -> None:
        ...

    @abstractmethod
    async def reorder_images(self, product_id: UUID, ordered_ids: list[UUID]) -> None:
        ...

    @abstractmethod
    async def delete_image(self, image_id: UUID) -> ProductImage:
        ...
