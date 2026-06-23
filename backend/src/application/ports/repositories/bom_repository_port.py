from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.models.bom import BOM, BOMItem


class BOMRepositoryPort(ABC):
    """Puerto abstracto para persistencia de BOM y sus items."""

    @abstractmethod
    async def get_bom_by_product_id(self, product_id: UUID) -> BOM | None:
        """
        Retorna la BOM activa asociada al producto terminado indicado.
        No incluye los items; usar get_bom_with_items para eso.
        """
        ...

    @abstractmethod
    async def create_bom(self, bom: BOM) -> BOM:
        """
        Persiste una nueva BOM. Los items en bom.items se persisten en cascada.
        Retorna la entidad con id y timestamps asignados por la BD.
        """
        ...

    @abstractmethod
    async def update_bom(self, bom: BOM) -> BOM:
        """
        Actualiza los campos de la cabecera (output_quantity, labor_minutes, notes, is_active).
        NO reemplaza los items — usar add/update/remove_bom_item para eso.
        """
        ...

    @abstractmethod
    async def delete_bom(self, bom_id: UUID) -> None:
        """
        Elimina la BOM y sus items en cascada (CASCADE definido en FK de bom_items).
        Lanza NotFoundError si bom_id no existe.
        """
        ...

    @abstractmethod
    async def get_bom_with_items(self, bom_id: UUID) -> tuple[BOM, list[BOMItem]]:
        """
        Retorna la BOM y su lista de items (eager load).
        Lanza NotFoundError si bom_id no existe.
        """
        ...

    @abstractmethod
    async def add_bom_item(self, item: BOMItem) -> BOMItem:
        """
        Agrega un nuevo item a una BOM existente.
        Lanza AlreadyExistsError si (bom_id, material_id) ya existe.
        Lanza NotFoundError si bom_id o material_id no existen.
        """
        ...

    @abstractmethod
    async def remove_bom_item(self, bom_item_id: UUID) -> None:
        """
        Elimina el item indicado.
        Lanza NotFoundError si bom_item_id no existe.
        """
        ...

    @abstractmethod
    async def update_bom_item(self, item: BOMItem) -> BOMItem:
        """
        Actualiza quantity_required, scrap_factor, notes y sort_order del item.
        Lanza NotFoundError si item.id no existe.
        """
        ...
