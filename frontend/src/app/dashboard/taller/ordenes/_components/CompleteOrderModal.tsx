"use client";

import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { workshopService } from "@/services/workshop.service";
import type { ProductionOrder } from "@/types/production";
import {
  completeProductionOrderSchema,
  type CompleteProductionOrderFormData,
} from "@/schemas/production.schema";
import { Modal } from "@/components/ui/Modal";
import { FormField, TextAreaField } from "@/components/ui/FormField";
import { Button } from "@/components/ui/Button";
import { formatCurrency } from "@/lib/formatters";

interface CompleteOrderModalProps {
  order: ProductionOrder;
  onClose: () => void;
  onCompleted: () => void;
}

export function CompleteOrderModal({
  order,
  onClose,
  onCompleted,
}: CompleteOrderModalProps) {
  // La lista no trae ítems; los cargamos con el detalle completo.
  const [items, setItems] = useState(order.items);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<CompleteProductionOrderFormData>({
    resolver: zodResolver(completeProductionOrderSchema),
    defaultValues: { quantity_produced: order.quantity_to_produce },
  });

  useEffect(() => {
    workshopService
      .getOrder(order.id)
      .then((full) => setItems(full.items))
      .catch(() => {});
  }, [order.id]);

  const quantityProduced = Number(watch("quantity_produced")) || 0;
  const totalEstimated = items.reduce(
    (acc, i) => acc + i.quantity_required * quantityProduced * i.unit_cost_snapshot,
    0,
  );

  const onSubmit = async (data: CompleteProductionOrderFormData) => {
    setServerError(null);
    try {
      await workshopService.completeOrder(order.id, data);
      onCompleted();
      onClose();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response
        ?.data?.detail;
      setServerError(
        typeof detail === "string"
          ? detail
          : (detail as { message?: string })?.message ?? "Error al completar la orden",
      );
    }
  };

  return (
    <Modal open onClose={onClose} title={`Completar ${order.order_number}`}>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm">
          <p className="font-medium text-amber-800 mb-1">
            Materiales que se descontarán:
          </p>
          <ul className="space-y-1">
            {items.map((item) => {
              const consumed = item.quantity_required * quantityProduced;
              return (
                <li key={item.id} className="flex justify-between text-amber-700">
                  <span>{item.material_name || item.material_sku || "Material"}</span>
                  <span className="font-mono">
                    -{consumed.toFixed(3)} × {formatCurrency(item.unit_cost_snapshot)} ={" "}
                    {formatCurrency(consumed * item.unit_cost_snapshot)}
                  </span>
                </li>
              );
            })}
          </ul>
          <p className="mt-2 font-medium text-amber-800 border-t border-amber-200 pt-2">
            Costo total estimado: {formatCurrency(totalEstimated)}
          </p>
        </div>

        <div>
          <FormField
            label="Cantidad producida efectivamente"
            type="number"
            step="0.001"
            min="0.001"
            max={order.quantity_to_produce}
            error={errors.quantity_produced?.message}
            {...register("quantity_produced")}
          />
          <p className="text-xs text-gray-400 mt-1">
            Planificada: {order.quantity_to_produce}
          </p>
        </div>

        <TextAreaField
          label="Notas (opcional)"
          placeholder="Observaciones del proceso…"
          error={errors.notes?.message}
          {...register("notes")}
        />

        <p className="text-xs text-red-600 bg-red-50 border border-red-200 rounded p-2">
          Esta acción es irreversible. Se descontarán los materiales del inventario y se
          acreditará el producto terminado.
        </p>

        {serverError && (
          <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
            {serverError}
          </p>
        )}

        <div className="flex justify-end gap-3 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" loading={isSubmitting}>
            Confirmar Completado
          </Button>
        </div>
      </form>
    </Modal>
  );
}
