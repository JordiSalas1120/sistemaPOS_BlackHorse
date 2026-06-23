from pydantic import BaseModel


class MessageResponse(BaseModel):
    message: str

    model_config = {"json_schema_extra": {"example": {"message": "Operación exitosa"}}}


class PaginationMeta(BaseModel):
    total: int
    skip: int
    limit: int
