import uuid
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from src.application.exceptions import NotFoundError
from src.application.ports.repositories.product_image_repository_port import (
    ProductImageRepositoryPort,
)
from src.application.ports.repositories.product_repository_port import ProductRepositoryPort
from src.config import settings
from src.dependencies import get_product_image_repo, get_product_repo
from src.domain.models.catalog import ProductImage
from src.infrastructure.api.v1.schemas.product_image_schema import (
    ProductImageResponse,
    ReorderImagesRequest,
)

router = APIRouter(prefix="/products/{product_id}/images", tags=["Imágenes de Producto"])

# Tipos MIME aceptados y su extensión correspondiente
ALLOWED_CONTENT_TYPES: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


def _validate_image(file: UploadFile) -> str:
    """Valida tipo MIME y retorna la extensión. Lanza HTTPException si es inválido."""
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Tipo de archivo no permitido: {file.content_type}. "
            f"Aceptados: {', '.join(ALLOWED_CONTENT_TYPES)}",
        )
    return ALLOWED_CONTENT_TYPES[file.content_type]


async def _read_and_validate_size(file: UploadFile) -> bytes:
    """Lee el contenido y valida que no supere MAX_FILE_SIZE_BYTES."""
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Imagen demasiado grande. Máximo permitido: {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB",
        )
    return contents


def _build_media_url(product_id: UUID, filename: str) -> str:
    """Construye la URL pública de la imagen."""
    return f"{settings.media_base_url.rstrip('/')}/media/{product_id}/{filename}"


def _save_to_disk(product_id: UUID, filename: str, contents: bytes) -> Path:
    """Guarda el archivo en MEDIA_LOCAL_PATH/{product_id}/{filename}."""
    dest_dir = Path(settings.media_local_path) / str(product_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / filename
    dest_path.write_bytes(contents)
    return dest_path


def _to_response(img: ProductImage) -> ProductImageResponse:
    return ProductImageResponse(
        id=img.id,
        product_id=img.product_id,
        url=img.url,
        alt_text=img.alt_text,
        sort_order=img.sort_order,
        is_primary=img.is_primary,
        created_at=img.created_at,
    )


@router.post(
    "",
    response_model=ProductImageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Subir imagen de producto",
)
async def upload_product_image(
    product_id: UUID,
    file: UploadFile = File(..., description="Archivo de imagen (jpg/png/webp, máx. 5MB)"),
    alt_text: str | None = Form(None),
    product_repo: ProductRepositoryPort = Depends(get_product_repo),
    image_repo: ProductImageRepositoryPort = Depends(get_product_image_repo),
):
    product = await product_repo.get_by_id(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    extension = _validate_image(file)
    contents = await _read_and_validate_size(file)

    filename = f"{uuid.uuid4()}{extension}"
    _save_to_disk(product_id, filename, contents)
    url = _build_media_url(product_id, filename)

    existing = await image_repo.get_images_for_product(product_id)
    is_first = len(existing) == 0

    image = ProductImage(
        id=uuid.uuid4(),
        product_id=product_id,
        url=url,
        alt_text=alt_text,
        sort_order=len(existing),
        is_primary=is_first,
        created_at=datetime.now(timezone.utc),
    )
    saved = await image_repo.add_image(image)
    return _to_response(saved)


@router.get(
    "",
    response_model=list[ProductImageResponse],
    summary="Listar imágenes del producto",
)
async def list_product_images(
    product_id: UUID,
    image_repo: ProductImageRepositoryPort = Depends(get_product_image_repo),
):
    images = await image_repo.get_images_for_product(product_id)
    return [_to_response(img) for img in images]


@router.put(
    "/reorder",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Reordenar imágenes",
)
async def reorder_images(
    product_id: UUID,
    body: ReorderImagesRequest,
    image_repo: ProductImageRepositoryPort = Depends(get_product_image_repo),
):
    try:
        await image_repo.reorder_images(product_id, body.ordered_ids)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put(
    "/{image_id}/primary",
    response_model=ProductImageResponse,
    summary="Marcar imagen como principal",
)
async def set_primary_image(
    product_id: UUID,
    image_id: UUID,
    image_repo: ProductImageRepositoryPort = Depends(get_product_image_repo),
):
    try:
        await image_repo.set_primary_image(product_id, image_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    images = await image_repo.get_images_for_product(product_id)
    primary = next((img for img in images if img.id == image_id), None)
    if primary is None:
        raise HTTPException(status_code=404, detail="Imagen no encontrada tras actualizar")
    return _to_response(primary)


@router.delete(
    "/{image_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar imagen",
)
async def delete_image(
    product_id: UUID,
    image_id: UUID,
    image_repo: ProductImageRepositoryPort = Depends(get_product_image_repo),
):
    try:
        deleted = await image_repo.delete_image(image_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Borrar archivo físico (best-effort)
    file_path = Path(deleted.url.replace(settings.media_base_url, settings.media_local_path))
    try:
        if file_path.exists():
            file_path.unlink()
    except OSError:
        pass
