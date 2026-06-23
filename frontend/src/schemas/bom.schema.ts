import { z } from "zod";

export const bomItemSchema = z.object({
  material_id:       z.string().uuid("ID de material inválido"),
  quantity_required: z.coerce.number().positive("La cantidad debe ser mayor a 0"),
  scrap_factor:      z.coerce.number().min(0).max(0.9999).default(0),
  notes:             z.string().optional(),
});

export const createBOMSchema = z.object({
  output_quantity: z.coerce.number().positive("La cantidad producida debe ser mayor a 0").default(1),
  labor_minutes:   z.coerce.number().int().min(0).optional(),
  notes:           z.string().optional(),
  items: z
    .array(bomItemSchema)
    .min(1, "La receta debe tener al menos un material")
    .refine(
      (items) => {
        const ids = items.map((i) => i.material_id);
        return ids.length === new Set(ids).size;
      },
      { message: "No se puede repetir el mismo material en la receta" },
    ),
});

export type CreateBOMValues = z.infer<typeof createBOMSchema>;
export type BOMItemValues  = z.infer<typeof bomItemSchema>;
