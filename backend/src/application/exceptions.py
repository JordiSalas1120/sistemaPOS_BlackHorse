"""
Excepciones del dominio y de la capa de aplicación.
La capa de infraestructura (API) las captura y las convierte en respuestas HTTP.
"""


class DomainException(Exception):
    """Base para todas las excepciones de negocio."""


class NotFoundError(DomainException):
    def __init__(self, entity: str, identifier: str):
        super().__init__(f"{entity} no encontrado: {identifier}")
        self.entity = entity
        self.identifier = identifier


class AlreadyExistsError(DomainException):
    def __init__(self, entity: str, field: str, value: str):
        super().__init__(f"{entity} ya existe con {field}: '{value}'")
        self.entity = entity
        self.field = field
        self.value = value


class BusinessRuleViolation(DomainException):
    """Violación de una regla de negocio (no es un error de datos, es una restricción del dominio)."""


class InsufficientStockError(BusinessRuleViolation):
    def __init__(self, product_id: str, available: float, requested: float):
        super().__init__(
            f"Stock insuficiente para producto {product_id}: "
            f"disponible {available}, solicitado {requested}"
        )
        self.product_id = product_id
        self.available = available
        self.requested = requested
