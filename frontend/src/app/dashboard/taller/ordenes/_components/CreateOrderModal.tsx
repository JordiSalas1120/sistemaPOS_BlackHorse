"use client";

import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { workshopService } from "@/services/workshop.service";
import type { WorkshopProduct, BOMWithCost } from "@/types/workshop";
import {
  createProductionOrderSchema,
  type CreateProductionOrderFormData,
} from "@/schemas/production.schema";
import { Modal } from "@/components/ui/Modal";
import { FormField, SelectField, TextAreaField } from "@/components/ui/FormField";
import { Button } from "@/components/ui/Button";
import { formatCurrency } from "@/lib/formatters";

interface CreateOrderModalProps {
  onClose: () => void;
  onCreated: () => void;
}

export function CreateOrderModal({ onClose, onCreated }: CreateOrderModalProps) {
  const [products, setProducts] = useState<WorkshopProduct[]>([]);
  const [bom, setBom] = useState<BOMWithCost | null>(null);
  const [bomError, setBomError] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<CreateProductionOrderFormData>({
    resolver: zodResolver(createProductionOrderSchema),
    defaultValues: { bom_id: "", quantity_to_produce: 1 },
  });

  useEffect(() => {
    workshopService
      .listFinishedProducts({ limit: 200 })
      .then((res) => setProducts(res.items))
      .catch(() => setProducts([]));
  }, []);

  const handleProductChange = async (productId: string) => {
    setBom(null);
    setBomError(null);
    setValue("bom_id", "");
    if (!productId) return;
    try {
      const loaded = await workshopService.getBOM(productId);
      setBom(loaded);
      setValue("bom_id", loaded.id, { shouldValidate: true });
    } catch {
      setBomError(
        "Este producto no tiene una receta (BOM) definida. Creala primero en el Taller.",
      );
    }
  };

  const quantity = Number(watch("quantity_to_produce")) || 0;
  const estimatedPerUnit = bom?.cost_per_unit ?? 0;

  const onSubmit = async (data: CreateProductionOrderFormData) => {
    setServerError(null);
    try {
      await workshopService.createOrder(data);
      onCreated();
      onClose();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response
        ?.data?.detail;
      setServerError(typeof detail === "string" ? detail : "Error al crear la orden");
    }
  };

  return (
    <Modal open onClose={onClose} title="Nueva orden de producción">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <SelectField
          label="Producto terminado *"
          error={bomError ?? (errors.bom_id?.message as string | undefined)}
          onChange={(e) => handleProductChange(e.target.value)}
          defaultValue=""
        >
          <option value="">Seleccionar…</option>
          {products.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name} ({p.sku})
            </option>
          ))}
        </SelectField>
        <input type="hidden" {...register("bom_id")} />

        {bom && (
          <div className="bg-brand-50 border border-brand-100 rounded-lg p-3 text-sm text-brand-700">
            Receta con <b>{bom.items.length}</b> material(es). Costo estimado por unidad:{" "}
            <b>{formatCurrency(estimatedPerUnit)}</b>
            {quantity > 0 && (
              <>
                {" "}— Total estimado lote:{" "}
                <b>{formatCurrency(estimatedPerUnit * quantity)}</b>
              </>
            )}
          </div>
        )}

        <FormField
          label="Cantidad a producir *"
          type="number"
          step="0.001"
          min="0.001"
          error={errors.quantity_to_produce?.message}
          {...register("quantity_to_produce")}
        />

        <FormField
          label="Artífice / operario *"
          placeholder="Nombre de quien produce"
          error={errors.produced_by?.message}
          {...register("produced_by")}
        />

        <TextAreaField
          label="Notas (opcional)"
          placeholder="Observaciones de la orden…"
          error={errors.notes?.message}
          {...register("notes")}
        />

        {serverError && (
          <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
            {serverError}
          </p>
        )}

        <div className="flex justify-end gap-3 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" loading={isSubmitting} disabled={!bom}>
            Crear orden
          </Button>
        </div>
      </form>
    </Modal>
  );
}
