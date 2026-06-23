"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { inventoryService } from "@/services/inventory.service";
import { adjustStockSchema } from "@/schemas/sale.schema";
import type { AdjustStockValues } from "@/schemas/sale.schema";
import type { InventoryItem, InventoryMovement } from "@/types";
import { FormField, SelectField, TextAreaField } from "@/components/ui/FormField";
import { Button } from "@/components/ui/Button";

const MOVEMENT_LABELS: Record<string, string> = {
  purchase: "Compra / Entrada",
  adjustment: "Ajuste de inventario",
  return: "Devolución de cliente",
  loss: "Merma / Pérdida",
};

interface AdjustStockFormProps {
  item: InventoryItem;
  onSuccess: (m: InventoryMovement) => void;
  onCancel: () => void;
}

export function AdjustStockForm({ item, onSuccess, onCancel }: AdjustStockFormProps) {
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<AdjustStockValues>({
    resolver: zodResolver(adjustStockSchema),
    defaultValues: {
      product_id: item.product_id,
      movement_type: "purchase",
    },
  });

  const onSubmit = async (values: AdjustStockValues) => {
    setServerError(null);
    try {
      const result = await inventoryService.adjust({
        product_id: values.product_id,
        quantity_delta: values.quantity_delta,
        movement_type: values.movement_type as InventoryMovement["movement_type"],
        notes: values.notes,
      });
      onSuccess(result);
    } catch (e: unknown) {
      setServerError(e instanceof Error ? e.message : "Error al ajustar stock");
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="bg-gray-50 rounded-lg px-4 py-3 text-sm">
        <div className="font-medium text-gray-900">{item.product_name}</div>
        <div className="text-gray-500 font-mono text-xs mt-0.5">{item.product_sku}</div>
        <div className="mt-2 text-gray-600">
          Stock actual:{" "}
          <span className="font-semibold text-gray-900">{item.quantity_on_hand}</span>
        </div>
      </div>

      <SelectField
        label="Tipo de movimiento"
        error={errors.movement_type?.message}
        {...register("movement_type")}
      >
        {Object.entries(MOVEMENT_LABELS).map(([value, label]) => (
          <option key={value} value={value}>{label}</option>
        ))}
      </SelectField>

      <FormField
        label="Cantidad (negativo para salidas)"
        type="number"
        step="0.001"
        placeholder="10"
        error={errors.quantity_delta?.message}
        {...register("quantity_delta")}
      />

      <div className="space-y-1">
        <label className="block text-sm font-medium text-gray-700">Notas</label>
        <textarea
          rows={2}
          placeholder="Motivo del ajuste…"
          className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-400 resize-none"
          {...register("notes")}
        />
      </div>

      {serverError && (
        <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
          {serverError}
        </p>
      )}

      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancelar
        </Button>
        <Button type="submit" loading={isSubmitting}>
          Registrar movimiento
        </Button>
      </div>
    </form>
  );
}
