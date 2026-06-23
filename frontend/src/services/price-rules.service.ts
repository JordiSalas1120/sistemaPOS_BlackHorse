import { api } from "@/lib/api";

export interface PriceRule {
  id: string;
  name: string;
  rule_type: string;
  discount_type: string;
  discount_value: number;
  priority: number;
  is_active: boolean;
  created_at: string;
  client_type_trigger: string | null;
  category_id: string | null;
  product_id: string | null;
  min_quantity: number | null;
  valid_from: string | null;
  valid_until: string | null;
}

export interface CreatePriceRuleInput {
  name: string;
  rule_type: string;
  discount_type: string;
  discount_value: number;
  priority?: number;
  client_type_trigger?: string;
  category_id?: string;
  product_id?: string;
  min_quantity?: number;
  valid_from?: string;
  valid_until?: string;
}

export const priceRulesService = {
  list: async (): Promise<PriceRule[]> => {
    const { data } = await api.get<PriceRule[]>("/price-rules");
    return data;
  },

  create: async (input: CreatePriceRuleInput): Promise<PriceRule> => {
    const { data } = await api.post<PriceRule>("/price-rules", input);
    return data;
  },

  toggle: async (id: string, is_active: boolean): Promise<PriceRule> => {
    const { data } = await api.patch<PriceRule>(`/price-rules/${id}/toggle`, null, {
      params: { is_active },
    });
    return data;
  },

  remove: async (id: string): Promise<void> => {
    await api.delete(`/price-rules/${id}`);
  },
};
