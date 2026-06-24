"use client";

import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { productsService } from "@/services/products.service";
import {
  createProductSchema,
  updateProductSchema,
  productUnitValues,
  productTypeValues,
  productTypeLabels,
} from "@/schemas/product.schema";
import type { CreateProductValues, UpdateProductValues } from "@/schemas/product.schema";
import type { Category, Product } from "@/types";
import { FormField, SelectField, TextAreaField } from "@/components/ui/FormField";
import { Button } from "@/components/ui/Button";
import { ImageGalleryAdmin } from "@/components/products/ImageGalleryAdmin";

interface ProductFormProps {
  product?: Product;          // si existe → modo edición
  onSuccess: (p: Product) => void;
  onCancel: () => void;
}

const UNIT_LABELS: Record<string, string> = {
  unidad: "Unidad",
  metro: "Metro",
  par: "Par",
  kg: "Kilogramo",
};

export function ProductForm({ product, onSuccess, onCancel }: ProductFormProps) {
  const isEdit = !!product;
  const [categories, setCategories] = useState<Category[]>([]);
  const [serverError, setServerError] = useState<string | null>(null);

  const schema = isEdit ? updateProductSchema : createProductSchema;
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<CreateProductValues | UpdateProductValues>({
    resolver: zodResolver(schema),
    defaultValues: product
      ? {
          name: product.name,
          description: product.description ?? "",
          category_id: product.category_id,
          base_price: product.base_price,
          wholesale_price: product.wholesale_price ?? undefined,
          unit: product.unit,
          is_active: product.is_active,
          product_type: product.product_type,
          show_in_catalog: product.show_in_catalog,
          cost_price: product.cost_price ?? undefined,
          modelo:
            typeof product.attributes?.modelo === "string"
              ? (product.attributes.modelo as string)
              : "",
          componentes: Array.isArray(product.attributes?.componentes)
            ? (product.attributes.componentes as unknown[]).join("\n")
            : typeof product.attributes?.componentes === "string"
              ? (product.attributes.componentes as string)
              : "",
        }
      : { unit: "unidad", low_stock_threshold: 5, product_type: "resale", show_in_catalog: false },
  });

  const watchProductType = watch("product_type");

  useEffect(() => {
    productsService.listCategories().then(setCategories);
  }, []);

  const onSubmit = async (values: CreateProductValues | UpdateProductValues) => {
    setServerError(null);
    try {
      // Plegar los campos editoriales (modelo/componentes) dentro de attributes,
      // preservando cualquier otro atributo existente del producto.
      const { modelo, componentes, ...rest } = values as CreateProductValues & {
        modelo?: string;
        componentes?: string;
      };
      const attributes: Record<string, unknown> = { ...(product?.attributes ?? {}) };
      if (modelo && modelo.trim()) attributes.modelo = modelo.trim();
      else delete attributes.modelo;
      const comps = (componentes ?? "")
        .split(/[\n,]/)
        .map((s) => s.trim())
        .filter(Boolean);
      if (comps.length) attributes.componentes = comps;
      else delete attributes.componentes;

      const payload = { ...rest, attributes };

      const result = isEdit
        ? await productsService.update(product!.id, payload as UpdateProductValues)
        : await productsService.create(payload as CreateProductValues);
      onSuccess(result);
    } catch (e: unknown) {
      setServerError(e instanceof Error ? e.message : "Error al guardar");
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      {isEdit && product && (
        <div className="bg-gray-50 rounded-lg px-4 py-2.5 text-sm flex items-center gap-3">
          <span className="text-gray-500">SKU</span>
          <span className="font-mono font-semibold text-gray-800">{product.sku}</span>
        </div>
      )}
      {!isEdit && (
        <p className="text-xs text-gray-400 bg-gray-50 rounded-lg px-3 py-2">
          El SKU se genera automáticamente según la categoría (ej: <span className="font-mono">EQU-00001</span>)
        </p>
      )}

      <FormField
        label="Nombre *"
        placeholder="Silla vaquera cuero"
        error={errors.name?.message}
        {...register("name")}
      />

      <div className="grid grid-cols-2 gap-4">
        <SelectField
          label="Categoría *"
          error={(errors as { category_id?: { message?: string } }).category_id?.message}
          {...register("category_id")}
        >
          <option value="">Seleccionar…</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </SelectField>

        <SelectField
          label="Unidad"
          {...register("unit")}
        >
          {productUnitValues.map((u) => (
            <option key={u} value={u}>{UNIT_LABELS[u]}</option>
          ))}
        </SelectField>
      </div>

      <SelectField
        label="Tipo de producto"
        {...register("product_type")}
      >
        {productTypeValues.map((v) => (
          <option key={v} value={v}>{productTypeLabels[v]}</option>
        ))}
      </SelectField>

      {(watchProductType === "raw_material" || watchProductType === "supply") && (
        <FormField
          label="Costo de compra (Bs.)"
          type="number"
          step="0.01"
          placeholder="0.00"
          error={(errors as { cost_price?: { message?: string } }).cost_price?.message}
          {...register("cost_price")}
        />
      )}

      {(watchProductType === "finished_product" || watchProductType === "resale") && (
        <div className="space-y-4 rounded-lg border border-brand-100 bg-brand-50/50 p-4">
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input type="checkbox" {...register("show_in_catalog")} className="rounded border-gray-300" />
            <span className="font-medium text-brand-800">Mostrar en catálogo público</span>
          </label>

          <FormField
            label="Modelo (catálogo)"
            placeholder="Ej: Montura Beniana"
            error={(errors as { modelo?: { message?: string } }).modelo?.message}
            {...register("modelo")}
          />

          <TextAreaField
            label="Componentes / características (uno por línea)"
            placeholder={"Estribos\nCaronas\nManta\nColcha"}
            error={(errors as { componentes?: { message?: string } }).componentes?.message}
            {...register("componentes")}
          />
          <p className="text-xs text-brand-400 -mt-2">
            Se muestran como características en el catálogo y la revista.
          </p>
        </div>
      )}

      <div className="grid grid-cols-2 gap-4">
        <FormField
          label="Precio retail (Bs.) *"
          type="number"
          step="0.01"
          placeholder="45000"
          error={errors.base_price?.message}
          {...register("base_price")}
        />
        <FormField
          label="Precio mayorista (Bs.)"
          type="number"
          step="0.01"
          placeholder="38000"
          error={errors.wholesale_price?.message}
          {...register("wholesale_price")}
        />
      </div>

      {!isEdit && (
        <FormField
          label="Umbral stock mínimo"
          type="number"
          step="1"
          placeholder="5"
          error={(errors as { low_stock_threshold?: { message?: string } }).low_stock_threshold?.message}
          {...register("low_stock_threshold")}
        />
      )}

      <TextAreaField
        label="Descripción"
        placeholder="Descripción opcional del producto…"
        error={errors.description?.message}
        {...register("description")}
      />

      {isEdit && (
        <label className="flex items-center gap-2 text-sm cursor-pointer">
          <input type="checkbox" {...register("is_active")} className="rounded border-gray-300" />
          Producto activo
        </label>
      )}

      {/* Galería de imágenes — solo en edición (requiere product.id existente) */}
      {isEdit && product && (
        <div className="border-t border-gray-100 pt-4">
          <ImageGalleryAdmin productId={product.id} />
        </div>
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
          {isEdit ? "Guardar cambios" : "Crear producto"}
        </Button>
      </div>
    </form>
  );
}
