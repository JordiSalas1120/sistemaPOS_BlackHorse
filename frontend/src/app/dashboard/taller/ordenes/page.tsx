"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { workshopService } from "@/services/workshop.service";
import type { ProductionOrder, ProductionOrderStatus } from "@/types/production";
import { OrderStatusBadge } from "@/components/ui/OrderStatusBadge";
import { Button } from "@/components/ui/Button";
import { formatCurrency, formatDate } from "@/lib/formatters";
import { CreateOrderModal } from "./_components/CreateOrderModal";
import { CompleteOrderModal } from "./_components/CompleteOrderModal";
import { CancelOrderModal } from "./_components/CancelOrderModal";

export default function TallerOrdenesPage() {
  const [orders, setOrders] = useState<ProductionOrder[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<ProductionOrderStatus | undefined>(
    undefined,
  );
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [completeOrder, setCompleteOrder] = useState<ProductionOrder | null>(null);
  const [cancelOrder, setCancelOrder] = useState<ProductionOrder | null>(null);

  const fetchOrders = useCallback(async () => {
    setLoading(true);
    try {
      const result = await workshopService.listOrders({ status: statusFilter, limit: 50 });
      setOrders(result.items);
      setTotal(result.total);
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    fetchOrders();
  }, [fetchOrders]);

  const handleStart = async (orderId: string) => {
    try {
      await workshopService.startOrder(orderId);
      await fetchOrders();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response
        ?.data?.detail as
        | { error_code?: string; product_id?: string; available?: number; requested?: number }
        | string
        | undefined;
      if (detail && typeof detail !== "string" && detail.error_code === "INSUFFICIENT_STOCK") {
        alert(
          `Stock insuficiente para iniciar la orden.\n` +
            `Material: ${detail.product_id}\n` +
            `Disponible: ${detail.available} — Requerido: ${detail.requested}`,
        );
      } else {
        alert(typeof detail === "string" ? detail : "Error al iniciar la orden");
      }
    }
  };

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <Link
            href="/dashboard/taller"
            className="text-xs text-brand-500 hover:underline"
          >
            ← Volver al Taller
          </Link>
          <h1 className="text-2xl font-bold text-brand-900">Órdenes de Producción</h1>
          <p className="text-sm text-gray-500 mt-1">{total} órdenes en total</p>
        </div>
        <Button onClick={() => setShowCreateModal(true)}>Nueva Orden</Button>
      </div>

      {/* Filtros de estado */}
      <div className="flex gap-2 mb-4 flex-wrap">
        {(
          [
            [undefined, "Todas"],
            ["draft", "Borrador"],
            ["in_progress", "En progreso"],
            ["completed", "Completadas"],
            ["cancelled", "Canceladas"],
          ] as [ProductionOrderStatus | undefined, string][]
        ).map(([val, label]) => (
          <button
            key={label}
            onClick={() => setStatusFilter(val)}
            className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
              statusFilter === val
                ? "bg-brand-700 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Tabla */}
      {loading ? (
        <p className="text-gray-500">Cargando...</p>
      ) : orders.length === 0 ? (
        <p className="text-gray-400 text-center py-12">
          No hay órdenes{statusFilter ? ` en estado "${statusFilter}"` : ""}.
        </p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Número</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Producto</th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">Cantidad</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Estado</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Artífice</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Fecha</th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">Costo est./u</th>
                <th className="px-4 py-3 text-center font-medium text-gray-600">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {orders.map((order) => (
                <tr key={order.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono font-medium text-brand-700">
                    {order.order_number}
                  </td>
                  <td className="px-4 py-3">
                    <div className="font-medium">{order.finished_product_name}</div>
                    <div className="text-xs text-gray-400">
                      {order.finished_product_sku}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right">
                    {order.quantity_produced}/{order.quantity_to_produce}
                  </td>
                  <td className="px-4 py-3">
                    <OrderStatusBadge status={order.status} />
                  </td>
                  <td className="px-4 py-3">{order.produced_by}</td>
                  <td className="px-4 py-3 text-gray-500">{formatDate(order.created_at)}</td>
                  <td className="px-4 py-3 text-right">
                    {formatCurrency(order.estimated_cost_per_unit)}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex justify-center gap-1">
                      {order.status === "draft" && (
                        <>
                          <button
                            onClick={() => handleStart(order.id)}
                            className="text-xs px-2 py-1 bg-yellow-100 text-yellow-800 rounded hover:bg-yellow-200"
                          >
                            Iniciar
                          </button>
                          <button
                            onClick={() => setCancelOrder(order)}
                            className="text-xs px-2 py-1 bg-red-50 text-red-700 rounded hover:bg-red-100"
                          >
                            Cancelar
                          </button>
                        </>
                      )}
                      {order.status === "in_progress" && (
                        <>
                          <button
                            onClick={() => setCompleteOrder(order)}
                            className="text-xs px-2 py-1 bg-green-100 text-green-800 rounded hover:bg-green-200"
                          >
                            Completar
                          </button>
                          <button
                            onClick={() => setCancelOrder(order)}
                            className="text-xs px-2 py-1 bg-red-50 text-red-700 rounded hover:bg-red-100"
                          >
                            Cancelar
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Modales */}
      {showCreateModal && (
        <CreateOrderModal
          onClose={() => setShowCreateModal(false)}
          onCreated={fetchOrders}
        />
      )}
      {completeOrder && (
        <CompleteOrderModal
          order={completeOrder}
          onClose={() => setCompleteOrder(null)}
          onCompleted={fetchOrders}
        />
      )}
      {cancelOrder && (
        <CancelOrderModal
          order={cancelOrder}
          onClose={() => setCancelOrder(null)}
          onCancelled={fetchOrders}
        />
      )}
    </div>
  );
}
