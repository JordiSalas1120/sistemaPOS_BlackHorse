import { z } from "zod";

export const productUnitValues = ["unidad", "metro", "par", "kg"] as const;

export const productTypeValues = [
  "raw_material",
  "finished_product",
  "tool",
  "supply",
  "resale",
] as const;
export type ProductType = (typeof productTypeValues)[number];

export const productTypeLabels: Record<ProductType, string> = {
  raw_material:     "Materia Prima",
  finished_product: "Producto Terminado",
  tool:             "Herramienta",
  supply:           "Insumo",
  resale:           "Reventa",
};

export const createProductSchema = z.object({
  name: z.string().min(1, "Nombre requerido").max(200),
  sku: z.string().max(50).optional(),  // opcional — se genera automáticamente
  category_id: z.string().uuid("Categoría inválida"),
  base_price: z.coerce.number().positive("El precio debe ser mayor a 0"),
  unit: z.enum(productUnitValues),
  description: z.string().optional(),
  wholesale_price: z.coerce.number().positive().optional(),
  image_url: z.string().url("URL inválida").optional().or(z.literal("")),
  low_stock_threshold: z.coerce.number().min(0).default(5),
  product_type: z.enum(productTypeValues).default("resale"),
  show_in_catalog: z.boolean().default(false),
  cost_price: z.coerce.number().positive().optional(),
  // Campos editoriales del catálogo (se guardan dentro de attributes)
  modelo: z.string().max(120).optional(),
  componentes: z.string().max(2000).optional(),
});

export const updateProductSchema = z.object({
  name: z.string().min(1).max(200).optional(),
  description: z.string().optional(),
  category_id: z.string().uuid().optional(),
  base_price: z.coerce.number().positive().optional(),
  wholesale_price: z.coerce.number().positive().optional(),
  unit: z.enum(productUnitValues).optional(),
  image_url: z.string().url().optional().or(z.literal("")),
  is_active: z.boolean().optional(),
  product_type: z.enum(productTypeValues).optional(),
  show_in_catalog: z.boolean().optional(),
  cost_price: z.coerce.number().positive().optional(),
  modelo: z.string().max(120).optional(),
  componentes: z.string().max(2000).optional(),
});

export type CreateProductValues = z.infer<typeof createProductSchema>;
export type UpdateProductValues = z.infer<typeof updateProductSchema>;
