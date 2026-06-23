import { api } from "@/lib/api";
import type { ProductImageUpload } from "@/types/catalog";

export const productImagesService = {
  list: async (productId: string): Promise<ProductImageUpload[]> => {
    const { data } = await api.get<ProductImageUpload[]>(`/products/${productId}/images`);
    return data;
  },

  upload: async (
    productId: string,
    file: File,
    altText?: string,
  ): Promise<ProductImageUpload> => {
    const formData = new FormData();
    formData.append("file", file);
    if (altText) formData.append("alt_text", altText);
    const { data } = await api.post<ProductImageUpload>(
      `/products/${productId}/images`,
      formData,
      { headers: { "Content-Type": "multipart/form-data" } },
    );
    return data;
  },

  setPrimary: async (productId: string, imageId: string): Promise<ProductImageUpload> => {
    const { data } = await api.put<ProductImageUpload>(
      `/products/${productId}/images/${imageId}/primary`,
    );
    return data;
  },

  reorder: async (productId: string, orderedIds: string[]): Promise<void> => {
    await api.put(`/products/${productId}/images/reorder`, { ordered_ids: orderedIds });
  },

  delete: async (productId: string, imageId: string): Promise<void> => {
    await api.delete(`/products/${productId}/images/${imageId}`);
  },
};
