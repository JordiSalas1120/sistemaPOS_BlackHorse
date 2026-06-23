"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { clientsService } from "@/services/clients.service";
import { createClientSchema, updateClientSchema } from "@/schemas/client.schema";
import type { CreateClientValues, UpdateClientValues } from "@/schemas/client.schema";
import type { Client } from "@/types";
import { FormField, SelectField, TextAreaField } from "@/components/ui/FormField";
import { Button } from "@/components/ui/Button";

interface ClientFormProps {
  client?: Client;
  onSuccess: (c: Client) => void;
  onCancel: () => void;
}

export function ClientForm({ client, onSuccess, onCancel }: ClientFormProps) {
  const isEdit = !!client;
  const [serverError, setServerError] = useState<string | null>(null);

  const schema = isEdit ? updateClientSchema : createClientSchema;
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<CreateClientValues | UpdateClientValues>({
    resolver: zodResolver(schema),
    defaultValues: client
      ? {
          full_name: client.full_name,
          phone: client.phone,
          email: client.email ?? "",
          address: client.address ?? "",
          notes: client.notes ?? "",
          client_type: client.client_type,
          whatsapp_opt_in: client.whatsapp_opt_in,
          is_active: client.is_active,
        }
      : { client_type: "retail", whatsapp_opt_in: false, tags: [] },
  });

  const onSubmit = async (values: CreateClientValues | UpdateClientValues) => {
    setServerError(null);
    // Limpiar campos opcionales vacíos
    const clean = Object.fromEntries(
      Object.entries(values).filter(([, v]) => v !== "" && v !== undefined)
    );
    try {
      const result = isEdit
        ? await clientsService.update(client!.id, clean as UpdateClientValues)
        : await clientsService.create(clean as CreateClientValues);
      onSuccess(result);
    } catch (e: unknown) {
      setServerError(e instanceof Error ? e.message : "Error al guardar");
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <FormField
        label="Nombre completo *"
        placeholder="Juan Pérez"
        error={errors.full_name?.message}
        {...register("full_name")}
      />

      <div className="grid grid-cols-2 gap-4">
        <FormField
          label="Teléfono *"
          placeholder="+5491155552222"
          error={errors.phone?.message}
          {...register("phone")}
        />
        <FormField
          label="Email"
          type="email"
          placeholder="juan@ejemplo.com"
          error={errors.email?.message}
          {...register("email")}
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <SelectField
          label="Tipo de cliente"
          error={(errors as { client_type?: { message?: string } }).client_type?.message}
          {...register("client_type")}
        >
          <option value="retail">Retail</option>
          <option value="wholesale">Mayorista</option>
        </SelectField>

        <FormField
          label="Dirección"
          placeholder="Av. San Martín 1234"
          error={errors.address?.message}
          {...register("address")}
        />
      </div>

      <TextAreaField
        label="Notas internas"
        placeholder="Observaciones sobre el cliente…"
        error={errors.notes?.message}
        {...register("notes")}
      />

      <label className="flex items-center gap-2 text-sm cursor-pointer">
        <input type="checkbox" {...register("whatsapp_opt_in")} className="rounded border-gray-300" />
        Acepta notificaciones por WhatsApp
      </label>

      {isEdit && (
        <label className="flex items-center gap-2 text-sm cursor-pointer">
          <input type="checkbox" {...register("is_active")} className="rounded border-gray-300" />
          Cliente activo
        </label>
      )}

      {serverError && (
        <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
          {serverError}
        </p>
      )}

      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancelar
        </Button>
        <Button type="submit" loading={isSubmitting}>
          {isEdit ? "Guardar cambios" : "Crear cliente"}
        </Button>
      </div>
    </form>
  );
}
