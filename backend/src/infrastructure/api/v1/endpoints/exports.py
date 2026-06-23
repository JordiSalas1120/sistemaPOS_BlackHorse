"""
Endpoint de exportación — genera archivos descargables sin pasar por use cases
complejos: simplemente consulta repos y serializa con el adapter correspondiente.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response

from src.application.ports.repositories.inventory_repository_port import InventoryRepositoryPort
from src.application.ports.repositories.product_repository_port import ProductRepositoryPort
from src.application.ports.repositories.sale_repository_port import SaleRepositoryPort
from src.dependencies import get_inventory_repo, get_product_repo, get_sale_repo
from src.infrastructure.adapters.excel_exporter.excel_exporter import ExcelExporter
from src.infrastructure.adapters.txt_exporter.txt_exporter import TxtTicketExporter

router = APIRouter(prefix="/exports", tags=["Exportaciones"])

_excel = ExcelExporter()
_txt = TxtTicketExporter()


@router.get("/products/excel")
async def export_products_excel(
    active_only: bool = Query(True),
    product_repo: ProductRepositoryPort = Depends(get_product_repo),
    inventory_repo: InventoryRepositoryPort = Depends(get_inventory_repo),
):
    """Descarga el catálogo de productos como .xlsx."""
    products = await product_repo.list_all(active_only=active_only, limit=10000)
    inventories = {inv.product_id: inv for inv in await inventory_repo.list_all()}

    data = [
        {
            "SKU": p.sku,
            "Nombre": p.name,
            "Precio retail": float(p.base_price),
            "Precio mayorista": float(p.wholesale_price) if p.wholesale_price else "",
            "Unidad": p.unit,
            "Stock actual": float(inventories[p.id].quantity_on_hand) if p.id in inventories else "",
            "Activo": "Sí" if p.is_active else "No",
        }
        for p in products
    ]

    content = _excel.export(data, "productos")
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=productos.xlsx"},
    )


@router.get("/inventory/excel")
async def export_inventory_excel(
    inventory_repo: InventoryRepositoryPort = Depends(get_inventory_repo),
    product_repo: ProductRepositoryPort = Depends(get_product_repo),
):
    """Descarga el snapshot de inventario como .xlsx."""
    inventories = await inventory_repo.list_all()
    products = {p.id: p for p in await product_repo.list_all(active_only=True, limit=10000)}

    data = [
        {
            "SKU": products[inv.product_id].sku if inv.product_id in products else "—",
            "Producto": products[inv.product_id].name if inv.product_id in products else "—",
            "Stock actual": float(inv.quantity_on_hand),
            "Umbral mínimo": float(inv.low_stock_threshold),
            "Stock bajo": "Sí" if inv.is_low_stock() else "No",
        }
        for inv in inventories
        if inv.product_id in products
    ]

    content = _excel.export(data, "inventario")
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=inventario.xlsx"},
    )


@router.get("/sales/excel")
async def export_sales_excel(
    sale_repo: SaleRepositoryPort = Depends(get_sale_repo),
):
    """Descarga el historial de ventas como .xlsx."""
    sales = await sale_repo.list_all(limit=10000)

    data = [
        {
            "Número": s.sale_number,
            "Fecha": s.created_at.strftime("%d/%m/%Y %H:%M"),
            "Tipo": s.sale_type,
            "Estado": s.status,
            "Pago": s.payment_type,
            "Subtotal": float(s.subtotal),
            "Descuento": float(s.discount_total),
            "Total": float(s.total),
            "Vendedor": s.sold_by,
            "Ítems": len(s.items),
        }
        for s in sales
    ]

    content = _excel.export(data, "ventas")
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=ventas.xlsx"},
    )


@router.get("/sales/{sale_id}/ticket")
async def export_sale_ticket(
    sale_id: UUID,
    sale_repo: SaleRepositoryPort = Depends(get_sale_repo),
    product_repo: ProductRepositoryPort = Depends(get_product_repo),
):
    """Genera el ticket de texto plano de una venta."""
    sale = await sale_repo.get_by_id(sale_id)
    if not sale:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venta no encontrada")

    items = []
    for item in sale.items:
        product = await product_repo.get_by_id(item.product_id)
        items.append({
            "product_name": product.name if product else "—",
            "quantity": float(item.quantity),
            "unit_price": float(item.unit_price),
            "discount_amount": float(item.discount_amount),
            "subtotal": float(item.subtotal),
        })

    data = [{
        "sale_number": sale.sale_number,
        "created_at": sale.created_at.strftime("%d/%m/%Y %H:%M"),
        "sale_type": sale.sale_type,
        "payment_type": sale.payment_type,
        "sold_by": sale.sold_by,
        "discount_total": float(sale.discount_total),
        "total": float(sale.total),
        "items": items,
    }]

    content = _txt.export(data, sale.sale_number)
    return Response(
        content=content,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={sale.sale_number}.txt"},
    )
