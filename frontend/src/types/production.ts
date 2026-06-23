// ── Enums ─────────────────────────────────────────────────────────────────────
export type ProductionOrderStatus =
  | "draft"
  | "in_progress"
  | "completed"
  | "cancelled";

// ── Interfaces ────────────────────────────────────────────────────────────────
export interface ProductionOrderItem {
  id: string;
  order_id: string;
  material_id: string;
  material_sku: string;
  material_name: string;
  quantity_required: number;
  quantity_consumed: number;
  unit_cost_snapshot: number;
  subtotal_cost: number;
  notes: string | null;
}

export interface ProductionOrder {
  id: string;
  order_number: string;
  bom_id: string;
  finished_product_id: string;
  finished_product_name: string;
  finished_product_sku: string;
  quantity_to_produce: number;
  quantity_produced: number;
  status: ProductionOrderStatus;
  produced_by: string;
  estimated_cost_per_unit: number;
  unit_cost_snapshot: number | null;
  started_at: string | null;
  completed_at: string | null;
  cancelled_at: string | null;
  created_at: string;
  updated_at: string;
  notes: string | null;
  items: ProductionOrderItem[];
}

export interface ProductionOrderListResponse {
  items: ProductionOrder[];
  total: number;
  skip: number;
  limit: number;
}

// ── Input interfaces ──────────────────────────────────────────────────────────
export interface CreateProductionOrderInput {
  bom_id: string;
  quantity_to_produce: number;
  produced_by: string;
  notes?: string;
}

export interface CompleteProductionOrderInput {
  quantity_produced: number;
  notes?: string;
}

export interface CancelProductionOrderInput {
  reason: string;
}
