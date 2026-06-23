"""Tests para CrmTaggingService."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.domain.models.client import Client
from src.domain.models.enums import ClientType, PaymentType, SaleStatus, SaleType
from src.domain.models.sale import Sale
from src.domain.services.crm_tagging_service import (
    TAG_NEEDS_MAINTENANCE_REMINDER,
    TAG_WHOLESALE,
    CrmTaggingService,
)


@pytest.fixture
def service():
    return CrmTaggingService()


def make_client(client_type: ClientType = ClientType.RETAIL, tags: list[str] | None = None) -> Client:
    now = datetime.now(timezone.utc)
    return Client(
        id=uuid.uuid4(),
        full_name="Test Client",
        phone="+5491100000000",
        client_type=client_type,
        tags=tags or [],
        whatsapp_opt_in=False,
        is_active=True,
        created_at=now,
        updated_at=now,
    )


def make_sale(sale_type: SaleType = SaleType.RETAIL) -> Sale:
    now = datetime.now(timezone.utc)
    return Sale(
        id=uuid.uuid4(),
        sale_number="VTA-2026-00001",
        sale_type=sale_type,
        status=SaleStatus.COMPLETED,
        payment_type=PaymentType.CASH,
        subtotal=Decimal("1000"),
        discount_total=Decimal("0"),
        tax_total=Decimal("0"),
        total=Decimal("1000"),
        sold_by="api",
        created_at=now,
        updated_at=now,
    )


class TestApplyPostSaleTags:
    def test_venta_mayorista_agrega_tag_mayorista(self, service):
        client = make_client(ClientType.WHOLESALE)
        sale = make_sale(SaleType.WHOLESALE)
        added = service.apply_post_sale_tags(client, sale, [])
        assert TAG_WHOLESALE in added
        assert client.has_tag(TAG_WHOLESALE)

    def test_venta_retail_no_agrega_tag_mayorista(self, service):
        client = make_client(ClientType.RETAIL)
        sale = make_sale(SaleType.RETAIL)
        added = service.apply_post_sale_tags(client, sale, [])
        assert TAG_WHOLESALE not in added
        assert not client.has_tag(TAG_WHOLESALE)

    def test_categoria_equino_agrega_tag_mantenimiento(self, service):
        client = make_client()
        sale = make_sale()
        added = service.apply_post_sale_tags(client, sale, ["equino"])
        assert TAG_NEEDS_MAINTENANCE_REMINDER in added
        assert client.has_tag(TAG_NEEDS_MAINTENANCE_REMINDER)

    def test_categoria_bovino_agrega_tag_mantenimiento(self, service):
        client = make_client()
        sale = make_sale()
        added = service.apply_post_sale_tags(client, sale, ["bovino"])
        assert TAG_NEEDS_MAINTENANCE_REMINDER in added

    def test_categoria_accesorios_no_agrega_tag_mantenimiento(self, service):
        client = make_client()
        sale = make_sale()
        added = service.apply_post_sale_tags(client, sale, ["accesorios"])
        assert TAG_NEEDS_MAINTENANCE_REMINDER not in added

    def test_no_duplica_tag_si_ya_existe(self, service):
        client = make_client(ClientType.WHOLESALE, tags=[TAG_WHOLESALE])
        sale = make_sale(SaleType.WHOLESALE)
        added = service.apply_post_sale_tags(client, sale, [])
        assert TAG_WHOLESALE not in added
        assert client.tags.count(TAG_WHOLESALE) == 1

    def test_venta_mayorista_con_equino_agrega_ambos_tags(self, service):
        client = make_client(ClientType.WHOLESALE)
        sale = make_sale(SaleType.WHOLESALE)
        added = service.apply_post_sale_tags(client, sale, ["equino"])
        assert TAG_WHOLESALE in added
        assert TAG_NEEDS_MAINTENANCE_REMINDER in added

    def test_sin_cliente_no_hay_nada_que_taggear(self, service):
        """Verificar que el servicio funciona correctamente con lista vacía de slugs."""
        client = make_client()
        sale = make_sale()
        added = service.apply_post_sale_tags(client, sale, [])
        assert added == []
