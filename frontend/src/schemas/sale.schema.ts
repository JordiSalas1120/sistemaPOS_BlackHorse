import { z } from "zod";

const paymentTypeValues = ["cash", "transfer", "card", "mixed"] as const;
const saleTypeValues = ["retail", "wholesale"] as const;

export const createSaleSchema = z.object({
  items: z
    .array(
      z.object({
        product_id: z.string().uuid("Producto inválido"),
        quantity: z.coerce.number().positive("Cantidad debe ser mayor a 0"),
      })
    )
    .min(1, "La venta debe tener al menos un ítem"),
  payment_type: z.enum(paymentTypeValues, { required_error: "Tipo de pago requerido" }),
  sale_type: z.enum(saleTypeValues).default("retail"),
  client_id: z.string().uuid().optional(),
  notes: z.string().optional(),
});

export const adjustStockSchema = z.object({
  product_id: z.string().uuid("Producto inválido"),
  quantity_delta: z.coerce.number().refine((v) => v !== 0, "La cantidad no puede ser 0"),
  movement_type: z.enum(["sale", "purchase", "adjustment", "return", "loss"] as const),
  notes: z.string().optional(),
});

export type CreateSaleValues = z.infer<typeof createSaleSchema>;
export type AdjustStockValues = z.infer<typeof adjustStockSchema>;
