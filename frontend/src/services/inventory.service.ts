import { api } from "@/lib/api";
import type { AdjustStockInput, InventoryItem, InventoryMovement } from "@/types";

export const inventoryService = {
  snapshot: async (): Promise<InventoryItem[]> => {
    const { data } = await api.get<InventoryItem[]>("/inventory");
    return data;
  },

  alerts: async (): Promise<InventoryItem[]> => {
    const { data } = await api.get<InventoryItem[]>("/inventory/alerts");
    return data;
  },

  adjust: async (input: AdjustStockInput): Promise<InventoryMovement> => {
    const { data } = await api.post<InventoryMovement>("/inventory/adjust", input);
    return data;
  },

  movements: async (
    productId: string,
    params?: { skip?: number; limit?: number }
  ): Promise<InventoryMovement[]> => {
    const { data } = await api.get<InventoryMovement[]>(
      `/inventory/${productId}/movements`,
      { params }
    );
    return data;
  },
};
