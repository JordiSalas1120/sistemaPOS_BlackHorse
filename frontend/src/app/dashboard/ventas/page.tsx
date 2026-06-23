"use client";

import { useEffect, useState } from "react";
import { ShoppingCart, Plus, X, Eye, Download, Search, Filter } from "lucide-react";
import { salesService } from "@/services/sales.service";
import { formatCurrency, formatDate } from "@/lib/formatters";
import { Modal } from "@/components/ui/Modal";
import { POSForm } from "@/components/sales/POSForm";
import { Button } from "@/components/ui/Button";
import type { Sale, SaleStatus } from "@/types";

const STATUS_LABELS: Record<SaleStatus, string> = {
  draft: "Borrador",
  completed: "Completada",
  cancelled: "Cancelada",
  refunded: "Reembolsada",
};

const STATUS_COLORS: Record<SaleStatus, string> = {
  draft: "bg-gray-100 text-gray-600",
  completed: "bg-green-100 text-green-700",
  cancelled: "bg-red-100 text-red-600",
  refunded: "bg-blue-100 text-blue-700",
};

const SALE_TYPE_LABELS: Record<string, string> = {
  retail: "Retail",
  wholesale: "Mayorista",
};

const PAYMENT_LABELS: Record<string, string> = {
  cash: "Efectivo",
  transfer: "Transferencia",
  card: "Tarjeta",
  mixed: "Combinado",
};

export default function VentasPage() {
  const [sales, setSales] = useState<Sale[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [posOpen, setPosOpen] = useState(false);
  const [cancelling, setCancelling] = useState<string | null>(null);
  const [detail, setDetail] = useState<Sale | null>(null);

  // Filtros
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<SaleStatus | "">("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const load = () => {
    setLoading(true);
    salesService
      .list({
        limit: 200,
        status: statusFilter || undefined,
        date_from: dateFrom ? new Date(dateFrom).toISOString() : undefined,
        date_to: dateTo ? new Date(dateTo + "T23:59:59").toISOString() : undefined,
      })
      .then((res) => { setSales(res.items); setTotal(res.total); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(load, [statusFilter, dateFrom, dateTo]);

  const filtered = search
    ? sales.filter(
        (s) =>
          s.sale_number.toLowerCase().includes(search.toLowerCase()) ||
          (s.notes ?? "").toLowerCase().includes(search.toLowerCase())
      )
    : sales;

  const handleCancel = async (id: string) => {
    if (!confirm("¿Cancelar esta venta? El stock se devolverá automáticamente.")) return;
    setCancelling(id);
    try {
      await salesService.cancel(id);
      load();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Error al cancelar");
    } finally {
      setCancelling(null);
    }
  };

  const handlePOSSuccess = (sale: Sale) => {
    setPosOpen(false);
    load();
    setDetail(sale);
  };

  const clearFilters = () => {
    setSearch("");
    setStatusFilter("");
    setDateFrom("");
    setDateTo("");
  };

  const hasFilters = search || statusFilter || dateFrom || dateTo;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Ventas</h1>
          <p className="text-sm text-gray-500 mt-0.5">{total} ventas registradas</p>
        </div>
        <div className="flex gap-2">
          <a
            href={`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/exports/sales/excel`}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50 text-gray-600 transition-colors"
          >
            <Download size={14} /> Excel
          </a>
          <Button onClick={() => setPosOpen(true)}>
            <Plus size={16} className="mr-1.5" />
            Nueva venta
          </Button>
        </div>
      </div>

      {/* Filtros */}
      <div className="flex flex-wrap gap-3 mb-4">
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Buscar por número…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8 pr-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-400 w-48"
          />
        </div>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as SaleStatus | "")}
          className="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-400 text-gray-700"
        >
          <option value="">Todos los estados</option>
          {(Object.entries(STATUS_LABELS) as [SaleStatus, string][]).map(([v, l]) => (
            <option key={v} value={v}>{l}</option>
          ))}
        </select>

        <div className="flex items-center gap-2">
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-400 text-gray-700"
          />
          <span className="text-gray-400 text-sm">—</span>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-400 text-gray-700"
          />
        </div>

        {hasFilters && (
          <button
            onClick={clearFilters}
            className="flex items-center gap-1 px-3 py-2 text-sm text-gray-500 hover:text-gray-700 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <X size={13} /> Limpiar
          </button>
        )}
      </div>

      {loading && <p className="text-sm text-gray-500">Cargando…</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}

      {!loading && !error && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Número</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Fecha</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Tipo</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Pago</th>
                <th className="text-right px-4 py-3 font-medium text-gray-600">Descuento</th>
                <th className="text-right px-4 py-3 font-medium text-gray-600 font-bold">Total</th>
                <th className="text-center px-4 py-3 font-medium text-gray-600">Estado</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-gray-400">
                    <ShoppingCart size={24} className="mx-auto mb-2 opacity-40" />
                    {hasFilters ? "Sin resultados para los filtros aplicados" : "Sin ventas registradas"}
                  </td>
                </tr>
              )}
              {filtered.map((s) => (
                <tr key={s.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-mono text-xs font-medium text-gray-700">{s.sale_number}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{formatDate(s.created_at)}</td>
                  <td className="px-4 py-3 text-gray-600">{SALE_TYPE_LABELS[s.sale_type] ?? s.sale_type}</td>
                  <td className="px-4 py-3 text-gray-600">{PAYMENT_LABELS[s.payment_type] ?? s.payment_type}</td>
                  <td className="px-4 py-3 text-right text-green-600">
                    {s.discount_total > 0 ? `-${formatCurrency(s.discount_total)}` : "—"}
                  </td>
                  <td className="px-4 py-3 text-right font-semibold text-gray-900">
                    {formatCurrency(s.total)}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[s.status]}`}>
                      {STATUS_LABELS[s.status]}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => setDetail(s)}
                        className="p-1.5 text-gray-400 hover:text-brand-600 transition-colors rounded"
                        title="Ver detalle"
                      >
                        <Eye size={14} />
                      </button>
                      {(s.status === "completed" || s.status === "draft") && (
                        <button
                          onClick={() => handleCancel(s.id)}
                          disabled={cancelling === s.id}
                          className="p-1.5 text-gray-400 hover:text-red-500 transition-colors rounded disabled:opacity-40"
                          title="Cancelar venta"
                        >
                          <X size={14} />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {filtered.length > 0 && (
            <div className="px-4 py-3 bg-gray-50 border-t border-gray-200 flex justify-between text-sm text-gray-600">
              <span>{filtered.length} venta{filtered.length !== 1 ? "s" : ""}</span>
              <span className="font-semibold">
                Total: {formatCurrency(filtered.reduce((acc, s) => acc + Number(s.total), 0))}
              </span>
            </div>
          )}
        </div>
      )}

      {/* POS modal */}
      <Modal open={posOpen} onClose={() => setPosOpen(false)} title="Nueva venta" width="max-w-4xl">
        <POSForm onSuccess={handlePOSSuccess} onCancel={() => setPosOpen(false)} />
      </Modal>

      {/* Detalle venta */}
      <Modal open={!!detail} onClose={() => setDetail(null)} title={`Venta ${detail?.sale_number}`} width="max-w-2xl">
        {detail && (
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div><span className="text-gray-500">Estado</span><div className="font-medium mt-0.5">{STATUS_LABELS[detail.status]}</div></div>
              <div><span className="text-gray-500">Tipo</span><div className="font-medium mt-0.5">{SALE_TYPE_LABELS[detail.sale_type]}</div></div>
              <div><span className="text-gray-500">Pago</span><div className="font-medium mt-0.5">{PAYMENT_LABELS[detail.payment_type]}</div></div>
            </div>

            <table className="w-full text-sm border border-gray-100 rounded-lg overflow-hidden">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left px-3 py-2 font-medium text-gray-600">Producto</th>
                  <th className="text-right px-3 py-2 font-medium text-gray-600">Cant.</th>
                  <th className="text-right px-3 py-2 font-medium text-gray-600">Precio unit.</th>
                  <th className="text-right px-3 py-2 font-medium text-gray-600">Descuento</th>
                  <th className="text-right px-3 py-2 font-medium text-gray-600">Subtotal</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {detail.items.map((item) => (
                  <tr key={item.id}>
                    <td className="px-3 py-2">
                      <div className="font-medium">{item.product_name}</div>
                      <div className="text-xs text-gray-400 font-mono">{item.product_sku}</div>
                    </td>
                    <td className="px-3 py-2 text-right">{item.quantity}</td>
                    <td className="px-3 py-2 text-right">{formatCurrency(item.unit_price)}</td>
                    <td className="px-3 py-2 text-right text-green-600">
                      {item.discount_amount > 0 ? `-${formatCurrency(item.discount_amount)}` : "—"}
                    </td>
                    <td className="px-3 py-2 text-right font-medium">{formatCurrency(item.subtotal)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot className="bg-gray-50 border-t border-gray-200">
                <tr>
                  <td colSpan={3} />
                  <td className="px-3 py-2 text-right text-sm font-semibold">Total</td>
                  <td className="px-3 py-2 text-right text-sm font-bold">{formatCurrency(detail.total)}</td>
                </tr>
              </tfoot>
            </table>

            {detail.notes && (
              <div className="text-sm text-gray-500 italic">Notas: {detail.notes}</div>
            )}

            <div className="flex justify-end pt-2">
              <a
                href={`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/exports/sales/${detail.id}/ticket`}
                className="inline-flex items-center gap-1.5 px-3 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50 text-gray-600 transition-colors"
              >
                <Download size={14} /> Descargar ticket
              </a>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
