import { api } from "@/lib/api";
import type {
  Category,
  CreateProductInput,
  Product,
  ProductListResponse,
  UpdateProductInput,
} from "@/types";

export const productsService = {
  list: async (params?: {
    active_only?: boolean;
    category_id?: string;
    skip?: number;
    limit?: number;
  }): Promise<ProductListResponse> => {
    const { data } = await api.get<ProductListResponse>("/products", { params });
    return data;
  },

  get: async (id: string): Promise<Product> => {
    const { data } = await api.get<Product>(`/products/${id}`);
    return data;
  },

  create: async (input: CreateProductInput): Promise<Product> => {
    const { data } = await api.post<Product>("/products", input);
    return data;
  },

  update: async (id: string, input: UpdateProductInput): Promise<Product> => {
    const { data } = await api.put<Product>(`/products/${id}`, input);
    return data;
  },

  remove: async (id: string): Promise<void> => {
    await api.delete(`/products/${id}`);
  },

  listCategories: async (): Promise<Category[]> => {
    const { data } = await api.get<Category[]>("/categories");
    return data;
  },
};
