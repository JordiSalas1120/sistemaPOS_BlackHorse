// ── Enums ─────────────────────────────────────────────────────────────────────
export type ClientType = "retail" | "wholesale";
export type SaleType = "retail" | "wholesale";
export type SaleStatus = "draft" | "completed" | "cancelled" | "refunded";
export type PaymentType = "cash" | "transfer" | "card" | "mixed";
export type MovementType = "sale" | "purchase" | "adjustment" | "return" | "loss";
export type ProductUnit = "unidad" | "metro" | "par" | "kg";
export type ProductType = "raw_material" | "finished_product" | "tool" | "supply" | "resale";

// ── Categorías ────────────────────────────────────────────────────────────────
export interface Category {
  id: string;
  name: string;
  slug: string;
  description: string | null;
}

// ── Productos ─────────────────────────────────────────────────────────────────
export interface Product {
  id: string;
  sku: string;
  name: string;
  category_id: string;
  category_name: string;
  base_price: number;
  wholesale_price: number | null;
  unit: ProductUnit;
  description: string | null;
  image_url: string | null;
  attributes: Record<string, unknown>;
  is_active: boolean;
  quantity_on_hand: number | null;
  product_type: ProductType;
  show_in_catalog: boolean;
  cost_price: number | null;
}

export interface ProductListResponse {
  items: Product[];
  total: number;
  skip: number;
  limit: number;
}

export interface CreateProductInput {
  name: string;
  sku?: string;  // opcional — se genera automáticamente en el backend
  category_id: string;
  base_price: number;
  unit: ProductUnit;
  description?: string;
  wholesale_price?: number;
  image_url?: string;
  attributes?: Record<string, unknown>;
  low_stock_threshold?: number;
  product_type?: ProductType;
  show_in_catalog?: boolean;
  cost_price?: number;
}

export interface UpdateProductInput {
  name?: string;
  description?: string;
  category_id?: string;
  base_price?: number;
  wholesale_price?: number;
  unit?: ProductUnit;
  image_url?: string;
  attributes?: Record<string, unknown>;
  is_active?: boolean;
  product_type?: ProductType;
  show_in_catalog?: boolean;
  cost_price?: number;
}

// ── Inventario ────────────────────────────────────────────────────────────────
export interface InventoryItem {
  product_id: string;
  product_sku: string;
  product_name: string;
  quantity_on_hand: number;
  low_stock_threshold: number;
  is_low_stock: boolean;
}

export interface InventoryMovement {
  id: string;
  product_id: string;
  movement_type: MovementType;
  quantity_delta: number;
  quantity_before: number;
  quantity_after: number;
  created_by: string;
  created_at: string;
  notes: string | null;
}

export interface AdjustStockInput {
  product_id: string;
  quantity_delta: number;
  movement_type: MovementType;
  notes?: string;
  reference_id?: string;
}

// ── Clientes ──────────────────────────────────────────────────────────────────
export interface Client {
  id: string;
  full_name: string;
  phone: string;
  email: string | null;
  address: string | null;
  client_type: ClientType;
  tags: string[];
  notes: string | null;
  whatsapp_opt_in: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  last_purchase_at: string | null;
}

export interface ClientListResponse {
  items: Client[];
  total: number;
  skip: number;
  limit: number;
}

export interface CreateClientInput {
  full_name: string;
  phone: string;
  client_type?: ClientType;
  email?: string;
  address?: string;
  notes?: string;
  whatsapp_opt_in?: boolean;
  tags?: string[];
}

export interface UpdateClientInput {
  full_name?: string;
  phone?: string;
  email?: string;
  address?: string;
  notes?: string;
  client_type?: ClientType;
  whatsapp_opt_in?: boolean;
  is_active?: boolean;
}

// ── Ventas ────────────────────────────────────────────────────────────────────
export interface SaleItem {
  id: string;
  sale_id: string;
  product_id: string;
  product_sku: string;
  product_name: string;
  quantity: number;
  unit_price: number;
  discount_amount: number;
  subtotal: number;
}

export interface Sale {
  id: string;
  sale_number: string;
  sale_type: SaleType;
  status: SaleStatus;
  payment_type: PaymentType;
  subtotal: number;
  discount_total: number;
  tax_total: number;
  total: number;
  sold_by: string;
  created_at: string;
  updated_at: string;
  items: SaleItem[];
  client_id: string | null;
  notes: string | null;
}

export interface SaleListResponse {
  items: Sale[];
  total: number;
  skip: number;
  limit: number;
}

export interface CreateSaleItemInput {
  product_id: string;
  quantity: number;
}

export interface CreateSaleInput {
  items: CreateSaleItemInput[];
  payment_type: PaymentType;
  sale_type?: SaleType;
  client_id?: string;
  notes?: string;
}
