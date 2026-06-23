"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { workshopService } from "@/services/workshop.service";
import type { ProductionOrder } from "@/types/production";
import {
  cancelProductionOrderSchema,
  type CancelProductionOrderFormData,
} from "@/schemas/production.schema";
import { Modal } from "@/components/ui/Modal";
import { TextAreaField } from "@/components/ui/FormField";
import { Button } from "@/components/ui/Button";

interface CancelOrderModalProps {
  order: ProductionOrder;
  onClose: () => void;
  onCancelled: () => void;
}

export function CancelOrderModal({ order, onClose, onCancelled }: CancelOrderModalProps) {
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<CancelProductionOrderFormData>({
    resolver: zodResolver(cancelProductionOrderSchema),
  });

  const onSubmit = async (data: CancelProductionOrderFormData) => {
    setServerError(null);
    try {
      await workshopService.cancelOrder(order.id, data);
      onCancelled();
      onClose();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response
        ?.data?.detail;
      setServerError(typeof detail === "string" ? detail : "Error al cancelar la orden");
    }
  };

  return (
    <Modal open onClose={onClose} title={`Cancelar ${order.order_number}`}>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        {order.status === "in_progress" && (
          <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded p-2">
            Esta orden está EN PROGRESO. La cancelación no revierte stock; verificá el
            inventario manualmente si ya se consumieron materiales.
          </p>
        )}

        <TextAreaField
          label="Motivo de la cancelación *"
          placeholder="Ej: Se agotó el cuero antes de iniciar la producción"
          error={errors.reason?.message}
          {...register("reason")}
        />

        {serverError && (
          <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
            {serverError}
          </p>
        )}

        <div className="flex justify-end gap-3 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Volver
          </Button>
          <Button type="submit" loading={isSubmitting}>
            Confirmar Cancelación
          </Button>
        </div>
      </form>
    </Modal>
  );
}
