import { z } from "zod";

export const createProductionOrderSchema = z.object({
  bom_id: z.string().uuid("Seleccioná un producto con receta válida"),
  quantity_to_produce: z.coerce
    .number({ invalid_type_error: "Ingresá una cantidad" })
    .positive("La cantidad debe ser mayor a 0")
    .max(9999, "Cantidad demasiado grande"),
  produced_by: z
    .string()
    .min(2, "Ingresá el nombre del artífice (mínimo 2 caracteres)")
    .max(100),
  notes: z.string().max(1000).optional(),
});

export const completeProductionOrderSchema = z.object({
  quantity_produced: z.coerce
    .number({ invalid_type_error: "Ingresá la cantidad producida" })
    .positive("La cantidad producida debe ser mayor a 0"),
  notes: z.string().max(1000).optional(),
});

export const cancelProductionOrderSchema = z.object({
  reason: z
    .string()
    .min(5, "Ingresá un motivo de al menos 5 caracteres")
    .max(500),
});

export type CreateProductionOrderFormData = z.infer<
  typeof createProductionOrderSchema
>;
export type CompleteProductionOrderFormData = z.infer<
  typeof completeProductionOrderSchema
>;
export type CancelProductionOrderFormData = z.infer<
  typeof cancelProductionOrderSchema
>;
