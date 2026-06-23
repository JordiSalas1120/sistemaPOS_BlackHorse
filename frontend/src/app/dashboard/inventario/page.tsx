"use client";

import { useEffect, useState } from "react";
import { Warehouse, AlertTriangle, ArrowUpDown, History } from "lucide-react";
import { inventoryService } from "@/services/inventory.service";
import { formatDate } from "@/lib/formatters";
import { Modal } from "@/components/ui/Modal";
import { AdjustStockForm } from "@/components/inventory/AdjustStockForm";
import { Button } from "@/components/ui/Button";
import type { InventoryItem, InventoryMovement } from "@/types";

const MOVEMENT_LABELS: Record<string, string> = {
  purchase: "Compra / Entrada",
  sale: "Venta",
  adjustment: "Ajuste",
  return: "Devolución",
  loss: "Merma / Pérdida",
};

const MOVEMENT_COLORS: Record<string, string> = {
  purchase: "text-green-600",
  return: "text-green-600",
  sale: "text-red-500",
  loss: "text-red-500",
  adjustment: "text-blue-600",
};

export default function InventarioPage() {
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAlertsOnly, setShowAlertsOnly] = useState(false);
  const [adjusting, setAdjusting] = useState<InventoryItem | null>(null);

  // Historial
  const [historyItem, setHistoryItem] = useState<InventoryItem | null>(null);
  const [movements, setMovements] = useState<InventoryMovement[]>([]);
  const [loadingMovements, setLoadingMovements] = useState(false);

  const load = () => {
    setLoading(true);
    inventoryService
      .snapshot()
      .then(setItems)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const openHistory = async (item: InventoryItem) => {
    setHistoryItem(item);
    setMovements([]);
    setLoadingMovements(true);
    try {
      const data = await inventoryService.movements(item.product_id, { limit: 50 });
      setMovements(data);
    } finally {
      setLoadingMovements(false);
    }
  };

  const displayed = showAlertsOnly ? items.filter((i) => i.is_low_stock) : items;
  const alertCount = items.filter((i) => i.is_low_stock).length;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Inventario</h1>
          <p className="text-sm text-gray-500 mt-0.5">{items.length} productos con stock</p>
        </div>
        {alertCount > 0 && (
          <div className="flex items-center gap-2 text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
            <AlertTriangle size={15} />
            {alertCount} con stock bajo
          </div>
        )}
      </div>

      <div className="flex items-center gap-3 mb-4">
        <label className="flex items-center gap-2 text-sm cursor-pointer">
          <input
            type="checkbox"
            checked={showAlertsOnly}
            onChange={(e) => setShowAlertsOnly(e.target.checked)}
            className="rounded border-gray-300 text-brand-600"
          />
          Solo alertas de stock bajo
        </label>
      </div>

      {loading && <p className="text-sm text-gray-500">Cargando…</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}

      {!loading && !error && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">SKU</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Producto</th>
                <th className="text-right px-4 py-3 font-medium text-gray-600">Stock actual</th>
                <th className="text-right px-4 py-3 font-medium text-gray-600">Umbral mínimo</th>
                <th className="text-center px-4 py-3 font-medium text-gray-600">Estado</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {displayed.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-gray-400">
                    <Warehouse size={24} className="mx-auto mb-2 opacity-40" />
                    {showAlertsOnly ? "Sin alertas de stock" : "Sin registros"}
                  </td>
                </tr>
              )}
              {displayed.map((item) => (
                <tr key={item.product_id} className={`hover:bg-gray-50 transition-colors ${item.is_low_stock ? "bg-amber-50/50" : ""}`}>
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">{item.product_sku}</td>
                  <td className="px-4 py-3 font-medium text-gray-900">{item.product_name}</td>
                  <td className="px-4 py-3 text-right">
                    <span className={item.quantity_on_hand <= 0 ? "text-red-600 font-bold" : item.is_low_stock ? "text-amber-600 font-semibold" : "text-gray-900"}>
                      {item.quantity_on_hand}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right text-gray-500">{item.low_stock_threshold}</td>
                  <td className="px-4 py-3 text-center">
                    {item.is_low_stock ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-amber-100 text-amber-700 rounded-full text-xs font-medium">
                        <AlertTriangle size={11} /> Stock bajo
                      </span>
                    ) : (
                      <span className="inline-block px-2 py-0.5 bg-green-100 text-green-700 rounded-full text-xs font-medium">OK</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => openHistory(item)}
                        className="p-1.5 text-gray-400 hover:text-brand-600 transition-colors rounded"
                        title="Ver historial"
                      >
                        <History size={14} />
                      </button>
                      <Button size="sm" variant="secondary" onClick={() => setAdjusting(item)}>
                        <ArrowUpDown size={13} className="mr-1" />
                        Ajustar
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal ajuste de stock */}
      <Modal
        open={!!adjusting}
        onClose={() => setAdjusting(null)}
        title="Ajuste de stock"
        width="max-w-md"
      >
        {adjusting && (
          <AdjustStockForm
            item={adjusting}
            onSuccess={() => { setAdjusting(null); load(); }}
            onCancel={() => setAdjusting(null)}
          />
        )}
      </Modal>

      {/* Modal historial de movimientos */}
      <Modal
        open={!!historyItem}
        onClose={() => setHistoryItem(null)}
        title={`Movimientos — ${historyItem?.product_name}`}
        width="max-w-2xl"
      >
        {loadingMovements && <p className="text-sm text-gray-500 py-4 text-center">Cargando historial…</p>}
        {!loadingMovements && movements.length === 0 && (
          <p className="text-sm text-gray-400 py-4 text-center">Sin movimientos registrados</p>
        )}
        {!loadingMovements && movements.length > 0 && (
          <div className="overflow-hidden rounded-lg border border-gray-100">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left px-3 py-2 font-medium text-gray-600">Tipo</th>
                  <th className="text-right px-3 py-2 font-medium text-gray-600">Cantidad</th>
                  <th className="text-right px-3 py-2 font-medium text-gray-600">Antes</th>
                  <th className="text-right px-3 py-2 font-medium text-gray-600">Después</th>
                  <th className="text-left px-3 py-2 font-medium text-gray-600">Fecha</th>
                  <th className="text-left px-3 py-2 font-medium text-gray-600">Notas</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {movements.map((m) => (
                  <tr key={m.id} className="hover:bg-gray-50">
                    <td className="px-3 py-2">
                      <span className={`font-medium ${MOVEMENT_COLORS[m.movement_type] ?? "text-gray-600"}`}>
                        {MOVEMENT_LABELS[m.movement_type] ?? m.movement_type}
                      </span>
                    </td>
                    <td className={`px-3 py-2 text-right font-semibold ${m.quantity_delta > 0 ? "text-green-600" : "text-red-500"}`}>
                      {m.quantity_delta > 0 ? "+" : ""}{m.quantity_delta}
                    </td>
                    <td className="px-3 py-2 text-right text-gray-500">{m.quantity_before}</td>
                    <td className="px-3 py-2 text-right text-gray-700 font-medium">{m.quantity_after}</td>
                    <td className="px-3 py-2 text-gray-500 text-xs whitespace-nowrap">{formatDate(m.created_at)}</td>
                    <td className="px-3 py-2 text-gray-400 text-xs">{m.notes ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Modal>
    </div>
  );
}
