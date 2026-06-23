import type {
  CatalogCategory,
  CatalogProduct,
  CatalogProductListResponse,
} from "@/types/catalog";

// El catálogo se renderiza en Server Components (SSR), por lo que el fetch corre
// dentro del contenedor del frontend. Ahí "localhost" NO es el backend, por eso
// se prefiere INTERNAL_API_URL (ej: http://backend:8000 en Docker). En local sin
// Docker cae a NEXT_PUBLIC_API_URL / localhost. Se normaliza para terminar en /api/v1.
const SERVER_API_BASE =
  process.env.INTERNAL_API_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000";
const API_URL = `${SERVER_API_BASE.replace(/\/+$/, "")}/api/v1`;

export const catalogService = {
  listProducts: async (params?: {
    category_slug?: string;
    search?: string;
    skip?: number;
    limit?: number;
  }): Promise<CatalogProductListResponse> => {
    const url = new URL(`${API_URL}/catalog/products`);
    if (params?.category_slug) url.searchParams.set("category_slug", params.category_slug);
    if (params?.search) url.searchParams.set("search", params.search);
    if (params?.skip != null) url.searchParams.set("skip", String(params.skip));
    if (params?.limit != null) url.searchParams.set("limit", String(params.limit));

    const res = await fetch(url.toString(), { next: { revalidate: 60 } });
    if (!res.ok) throw new Error(`Error ${res.status} al cargar catálogo`);
    return res.json();
  },

  getProductBySku: async (sku: string): Promise<CatalogProduct> => {
    const res = await fetch(`${API_URL}/catalog/products/${sku}`, {
      next: { revalidate: 60 },
    });
    if (res.status === 404) throw new Error("Producto no encontrado");
    if (!res.ok) throw new Error(`Error ${res.status}`);
    return res.json();
  },

  listCategories: async (): Promise<CatalogCategory[]> => {
    const res = await fetch(`${API_URL}/catalog/categories`, {
      next: { revalidate: 300 },
    });
    if (!res.ok) throw new Error(`Error ${res.status} al cargar categorías`);
    return res.json();
  },

  getRelatedProducts: async (sku: string): Promise<CatalogProduct[]> => {
    const res = await fetch(`${API_URL}/catalog/products/${sku}/related`, {
      next: { revalidate: 60 },
    });
    if (!res.ok) return [];
    return res.json();
  },
};
