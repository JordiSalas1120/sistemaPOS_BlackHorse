export interface CatalogImage {
  id: string;
  url: string;
  alt_text: string | null;
  sort_order: number;
  is_primary: boolean;
}

export interface CatalogProduct {
  id: string;
  sku: string;
  name: string;
  description: string | null;
  category_id: string;
  category_name: string;
  category_slug: string;
  unit: string;
  attributes: Record<string, unknown>;
  images: CatalogImage[];
  base_price: number | null; // null si CATALOG_SHOW_PRICES=false en el servidor
}

export interface CatalogProductListResponse {
  items: CatalogProduct[];
  total: number;
  skip: number;
  limit: number;
}

export interface CatalogCategory {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  product_count: number;
}

export interface ProductImageUpload {
  id: string;
  product_id: string;
  url: string;
  alt_text: string | null;
  sort_order: number;
  is_primary: boolean;
  created_at: string;
}
