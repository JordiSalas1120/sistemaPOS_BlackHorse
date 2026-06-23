import { ProductUnit } from "./index";

export type ProductType =
  | "raw_material"
  | "finished_product"
  | "tool"
  | "supply"
  | "resale";

export interface WorkshopProduct {
  id: string;
  sku: string;
  name: string;
  product_type: ProductType;
  category_id: string;
  base_price: number;
  unit: ProductUnit;
  is_active: boolean;
  show_in_catalog: boolean;
  cost_price: number | null;
  wholesale_price: number | null;
  description: string | null;
  quantity_on_hand: number | null;
}

export interface WorkshopProductListResponse {
  items: WorkshopProduct[];
  total: number;
  skip: number;
  limit: number;
  product_type: ProductType;
}

export interface BOMItem {
  id: string;
  bom_id: string;
  material_id: string;
  quantity_required: number;
  scrap_factor: number;
  effective_quantity: number;
  sort_order: number;
  notes: string | null;
}

export interface BOM {
  id: string;
  finished_product_id: string;
  output_quantity: number;
  is_active: boolean;
  labor_minutes: number | null;
  notes: string | null;
  items: BOMItem[];
}

export interface BOMWithCost extends BOM {
  total_material_cost: number | null;
  cost_per_unit: number | null;
  material_names: Record<string, string>;
}

export interface BOMCostLine {
  material_id: string;
  material_name: string;
  material_sku: string;
  unit: string;
  quantity_required: number;
  scrap_factor: number;
  effective_quantity: number;
  unit_price: number;
  subtotal: number;
}

export interface BOMCostDetail {
  bom_id: string;
  finished_product_id: string;
  output_quantity: number;
  lines: BOMCostLine[];
  total_material_cost: number;
  cost_per_unit: number;
  labor_minutes: number | null;
}

export interface CreateBOMInput {
  output_quantity: number;
  labor_minutes?: number;
  notes?: string;
  items: {
    material_id: string;
    quantity_required: number;
    scrap_factor?: number;
    notes?: string;
  }[];
}

export interface UpdateBOMInput extends Partial<Omit<CreateBOMInput, "items">> {
  is_active?: boolean;
  items?: CreateBOMInput["items"];
}
