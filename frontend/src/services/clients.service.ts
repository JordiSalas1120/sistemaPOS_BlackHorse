import { api } from "@/lib/api";
import type {
  Client,
  ClientListResponse,
  ClientType,
  CreateClientInput,
  UpdateClientInput,
} from "@/types";

export const clientsService = {
  list: async (params?: {
    active_only?: boolean;
    client_type?: ClientType;
    tag?: string;
    skip?: number;
    limit?: number;
  }): Promise<ClientListResponse> => {
    const { data } = await api.get<ClientListResponse>("/clients", { params });
    return data;
  },

  get: async (id: string): Promise<Client> => {
    const { data } = await api.get<Client>(`/clients/${id}`);
    return data;
  },

  create: async (input: CreateClientInput): Promise<Client> => {
    const { data } = await api.post<Client>("/clients", input);
    return data;
  },

  update: async (id: string, input: UpdateClientInput): Promise<Client> => {
    const { data } = await api.put<Client>(`/clients/${id}`, input);
    return data;
  },

  addTag: async (id: string, tag: string): Promise<Client> => {
    const { data } = await api.post<Client>(`/clients/${id}/tags`, { tag });
    return data;
  },

  removeTag: async (id: string, tag: string): Promise<Client> => {
    const { data } = await api.delete<Client>(`/clients/${id}/tags/${tag}`);
    return data;
  },
};
