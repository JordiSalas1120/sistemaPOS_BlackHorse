from src.domain.models.client import Client
from src.domain.models.sale import Sale

# Tags de CRM predefinidos
TAG_WHOLESALE = "mayorista"
TAG_HEAVY_CATTLE = "ganaderia_pesada"
TAG_NEEDS_MAINTENANCE_REMINDER = "recordatorio_mantenimiento"

# Categorías que activan recordatorio de mantenimiento
MAINTENANCE_CATEGORY_SLUGS = {"equino", "bovino"}


class CrmTaggingService:
    """
    Reglas puras para asignar/remover tags CRM a clientes
    en función de sus ventas.
    """

    def apply_post_sale_tags(
        self,
        client: Client,
        sale: Sale,
        sold_category_slugs: list[str],
    ) -> list[str]:
        """
        Evalúa qué tags deben agregarse al cliente tras una venta.
        Retorna la lista de tags nuevos añadidos.
        """
        added: list[str] = []

        if sale.is_wholesale() and not client.has_tag(TAG_WHOLESALE):
            client.add_tag(TAG_WHOLESALE)
            added.append(TAG_WHOLESALE)

        has_maintenance_category = any(
            slug in MAINTENANCE_CATEGORY_SLUGS for slug in sold_category_slugs
        )
        if has_maintenance_category and not client.has_tag(TAG_NEEDS_MAINTENANCE_REMINDER):
            client.add_tag(TAG_NEEDS_MAINTENANCE_REMINDER)
            added.append(TAG_NEEDS_MAINTENANCE_REMINDER)

        return added
