import { z } from "zod";

const clientTypeValues = ["retail", "wholesale"] as const;

export const createClientSchema = z.object({
  full_name: z.string().min(1, "Nombre requerido").max(200),
  phone: z.string().min(7, "Teléfono inválido").max(30),
  client_type: z.enum(clientTypeValues).default("retail"),
  email: z.string().email("Email inválido").optional().or(z.literal("")),
  address: z.string().optional(),
  notes: z.string().optional(),
  whatsapp_opt_in: z.boolean().default(false),
  tags: z.array(z.string()).default([]),
});

export const updateClientSchema = z.object({
  full_name: z.string().min(1).max(200).optional(),
  phone: z.string().min(7).max(30).optional(),
  email: z.string().email().optional().or(z.literal("")),
  address: z.string().optional(),
  notes: z.string().optional(),
  client_type: z.enum(clientTypeValues).optional(),
  whatsapp_opt_in: z.boolean().optional(),
  is_active: z.boolean().optional(),
});

export type CreateClientValues = z.infer<typeof createClientSchema>;
export type UpdateClientValues = z.infer<typeof updateClientSchema>;
