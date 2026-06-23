import { api } from "@/lib/api";
import type { CreateSaleInput, Sale, SaleListResponse, SaleStatus } from "@/types";

export const salesService = {
  list: async (params?: {
    client_id?: string;
    status?: SaleStatus;
    date_from?: string;
    date_to?: string;
    skip?: number;
    limit?: number;
  }): Promise<SaleListResponse> => {
    const { data } = await api.get<SaleListResponse>("/sales", { params });
    return data;
  },

  get: async (id: string): Promise<Sale> => {
    const { data } = await api.get<Sale>(`/sales/${id}`);
    return data;
  },

  create: async (input: CreateSaleInput): Promise<Sale> => {
    const { data } = await api.post<Sale>("/sales", input);
    return data;
  },

  cancel: async (id: string): Promise<void> => {
    await api.post(`/sales/${id}/cancel`);
  },
};
