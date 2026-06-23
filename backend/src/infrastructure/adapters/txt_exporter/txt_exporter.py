"""
Adapter de exportación a texto plano — genera tickets de venta estilo POS.
"""
from datetime import datetime, timezone

from src.application.ports.exporter_port import ExporterPort


class TxtTicketExporter(ExporterPort):
    """
    Genera un ticket de venta en texto plano de ancho fijo (40 caracteres).
    El campo `filename` se ignora — el contenido es siempre texto.
    """
    WIDTH = 40

    def export(self, data: list[dict], filename: str = "ticket") -> bytes:
        lines: list[str] = []
        sep = "─" * self.WIDTH

        lines.append(sep)
        lines.append(self._center("TALABARTERÍA"))
        lines.append(self._center("Comprobante de venta"))
        lines.append(sep)

        for sale in data:
            lines.append(f"Nro: {sale.get('sale_number', '—')}")
            lines.append(f"Fecha: {sale.get('created_at', '—')}")
            lines.append(f"Tipo: {sale.get('sale_type', '—').upper()}")
            lines.append(f"Pago: {sale.get('payment_type', '—').upper()}")
            if sale.get("client_name"):
                lines.append(f"Cliente: {sale['client_name']}")
            lines.append(sep)

            for item in sale.get("items", []):
                name = str(item.get("product_name", ""))[:22]
                qty = item.get("quantity", 1)
                price = float(item.get("unit_price", 0))
                subtotal = float(item.get("subtotal", price * qty))
                lines.append(f"  {name:<22} x{qty}")
                lines.append(f"  {'$ {:,.2f}'.format(price):>37}")
                if item.get("discount_amount", 0) > 0:
                    disc = float(item["discount_amount"])
                    lines.append(f"  {'Desc: -$ {:,.2f}'.format(disc):>37}")

            lines.append(sep)
            discount = float(sale.get("discount_total", 0))
            total = float(sale.get("total", 0))
            if discount > 0:
                lines.append(f"  {'Descuento total:':<20} -$ {discount:>10,.2f}")
            lines.append(f"  {'TOTAL:':<20}  $ {total:>10,.2f}")
            lines.append(sep)
            lines.append(self._center(f"Atendido por: {sale.get('sold_by', '—')}"))
            lines.append(self._center("¡Gracias por su compra!"))
            lines.append(sep)
            lines.append("")

        return "\n".join(lines).encode("utf-8")

    def _center(self, text: str) -> str:
        return text.center(self.WIDTH)
