from enum import StrEnum


class ClientType(StrEnum):
    RETAIL = "retail"
    WHOLESALE = "wholesale"


class SaleType(StrEnum):
    RETAIL = "retail"
    WHOLESALE = "wholesale"


class SaleStatus(StrEnum):
    DRAFT = "draft"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentType(StrEnum):
    CASH = "cash"
    TRANSFER = "transfer"
    CARD = "card"
    MIXED = "mixed"


class MovementType(StrEnum):
    SALE = "sale"
    PURCHASE = "purchase"
    ADJUSTMENT = "adjustment"
    RETURN = "return"
    LOSS = "loss"
    PRODUCTION_CONSUMPTION = "production_consumption"  # descuento de insumos
    PRODUCTION_OUTPUT = "production_output"             # acreditación del terminado


class ProductionOrderStatus(StrEnum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PriceRuleType(StrEnum):
    QUANTITY_THRESHOLD = "quantity_threshold"
    CLIENT_TYPE = "client_type"
    CATEGORY_DISCOUNT = "category_discount"


class DiscountType(StrEnum):
    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"


class ProductUnit(StrEnum):
    UNIT = "unidad"
    METER = "metro"
    PAIR = "par"
    KG = "kg"


class ProductType(StrEnum):
    RAW_MATERIAL = "raw_material"          # materia prima: cuero, hebilla, hilo
    FINISHED_PRODUCT = "finished_product"  # producto fabricado en taller: montura, jaquima
    TOOL = "tool"                          # herramienta del taller (no se vende)
    SUPPLY = "supply"                      # insumo consumible: adhesivo, cera
    RESALE = "resale"                      # artículo para reventa sin transformación


class AuditAction(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    SALE = "sale"
    CANCEL = "cancel"
    EXPORT = "export"
    SEND_MESSAGE = "send_message"
