import { api } from "@/lib/api";
import {
  BOMWithCost,
  BOM,
  BOMItem,
  CreateBOMInput,
  UpdateBOMInput,
  WorkshopProductListResponse,
} from "@/types/workshop";
import type {
  CancelProductionOrderInput,
  CompleteProductionOrderInput,
  CreateProductionOrderInput,
  ProductionOrder,
  ProductionOrderListResponse,
  ProductionOrderStatus,
} from "@/types/production";

interface ListParams {
  skip?: number;
  limit?: number;
  category_id?: string;
  search?: string;
  active_only?: boolean;
}

export const workshopService = {
  async listMaterials(params: ListParams = {}): Promise<WorkshopProductListResponse> {
    const { data } = await api.get<WorkshopProductListResponse>(
      "/workshop/materials",
      { params },
    );
    return data;
  },

  async listFinishedProducts(params: ListParams = {}): Promise<WorkshopProductListResponse> {
    const { data } = await api.get<WorkshopProductListResponse>(
      "/workshop/finished-products",
      { params },
    );
    return data;
  },

  async getBOM(productId: string): Promise<BOMWithCost> {
    const { data } = await api.get<BOMWithCost>(`/workshop/bom/${productId}`);
    return data;
  },

  async createBOM(productId: string, input: CreateBOMInput): Promise<BOM> {
    const { data } = await api.post<BOM>(`/workshop/bom/${productId}`, input);
    return data;
  },

  async updateBOM(productId: string, input: UpdateBOMInput): Promise<BOM> {
    const { data } = await api.put<BOM>(`/workshop/bom/${productId}`, input);
    return data;
  },

  async addBOMItem(
    productId: string,
    item: { material_id: string; quantity_required: number; scrap_factor?: number; notes?: string },
  ): Promise<BOMItem> {
    const { data } = await api.post<BOMItem>(
      `/workshop/bom/${productId}/items`,
      item,
    );
    return data;
  },

  async updateBOMItem(
    productId: string,
    itemId: string,
    patch: { quantity_required?: number; scrap_factor?: number; notes?: string; sort_order?: number },
  ): Promise<BOMItem> {
    const { data } = await api.put<BOMItem>(
      `/workshop/bom/${productId}/items/${itemId}`,
      patch,
    );
    return data;
  },

  async deleteBOMItem(productId: string, itemId: string): Promise<void> {
    await api.delete(`/workshop/bom/${productId}/items/${itemId}`);
  },

  // ── Órdenes de producción (Sprint 2) ──────────────────────────────────────

  async listOrders(params?: {
    status?: ProductionOrderStatus;
    finished_product_id?: string;
    produced_by?: string;
    date_from?: string;
    date_to?: string;
    skip?: number;
    limit?: number;
  }): Promise<ProductionOrderListResponse> {
    const { data } = await api.get<ProductionOrderListResponse>(
      "/workshop/orders",
      { params },
    );
    return data;
  },

  async getOrder(orderId: string): Promise<ProductionOrder> {
    const { data } = await api.get<ProductionOrder>(`/workshop/orders/${orderId}`);
    return data;
  },

  async createOrder(input: CreateProductionOrderInput): Promise<ProductionOrder> {
    const { data } = await api.post<ProductionOrder>("/workshop/orders", input);
    return data;
  },

  async startOrder(orderId: string): Promise<ProductionOrder> {
    const { data } = await api.post<ProductionOrder>(`/workshop/orders/${orderId}/start`);
    return data;
  },

  async completeOrder(
    orderId: string,
    input: CompleteProductionOrderInput,
  ): Promise<ProductionOrder> {
    const { data } = await api.post<ProductionOrder>(
      `/workshop/orders/${orderId}/complete`,
      input,
    );
    return data;
  },

  async cancelOrder(
    orderId: string,
    input: CancelProductionOrderInput,
  ): Promise<ProductionOrder> {
    const { data } = await api.post<ProductionOrder>(
      `/workshop/orders/${orderId}/cancel`,
      input,
    );
    return data;
  },

  // Contadores para el dashboard KPI
  async getInProgressCount(): Promise<number> {
    const result = await workshopService.listOrders({ status: "in_progress", limit: 1 });
    return result.total;
  },

  async getCompletedThisMonthCount(): Promise<number> {
    const now = new Date();
    const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
    const result = await workshopService.listOrders({
      status: "completed",
      date_from: firstDay.toISOString(),
      limit: 1,
    });
    return result.total;
  },
};
