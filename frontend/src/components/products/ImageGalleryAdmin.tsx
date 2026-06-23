"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import { productImagesService } from "@/services/product-images.service";
import type { ProductImageUpload } from "@/types/catalog";

interface ImageGalleryAdminProps {
  productId: string;
}

export function ImageGalleryAdmin({ productId }: ImageGalleryAdminProps) {
  const [images, setImages] = useState<ProductImageUpload[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    productImagesService
      .list(productId)
      .then((imgs) => setImages([...imgs].sort((a, b) => a.sort_order - b.sort_order)))
      .catch(() => {});
  }, [productId]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    if (files.length === 0) return;
    setUploading(true);
    setError(null);
    try {
      const uploaded: ProductImageUpload[] = [];
      for (const file of files) {
        const img = await productImagesService.upload(productId, file);
        uploaded.push(img);
      }
      setImages((prev) => [...prev, ...uploaded]);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al subir imagen");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleSetPrimary = async (imageId: string) => {
    try {
      await productImagesService.setPrimary(productId, imageId);
      setImages((prev) => prev.map((img) => ({ ...img, is_primary: img.id === imageId })));
    } catch {
      setError("Error al establecer imagen principal");
    }
  };

  const handleDelete = async (imageId: string) => {
    if (!confirm("¿Eliminar esta imagen?")) return;
    try {
      await productImagesService.delete(productId, imageId);
      setImages((prev) => prev.filter((img) => img.id !== imageId));
    } catch {
      setError("Error al eliminar imagen");
    }
  };

  const handleDragStart = (imageId: string) => setDragging(imageId);
  const handleDragOver = (e: React.DragEvent, targetId: string) => {
    e.preventDefault();
    if (!dragging || dragging === targetId) return;
    setImages((prev) => {
      const from = prev.findIndex((i) => i.id === dragging);
      const to = prev.findIndex((i) => i.id === targetId);
      const next = [...prev];
      const [item] = next.splice(from, 1);
      next.splice(to, 0, item);
      return next.map((img, idx) => ({ ...img, sort_order: idx }));
    });
  };
  const handleDrop = async () => {
    setDragging(null);
    try {
      await productImagesService.reorder(
        productId,
        images.map((img) => img.id),
      );
    } catch {
      setError("Error al reordenar imágenes");
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-brand-800">Galería de imágenes</h3>
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          className="text-sm bg-brand-600 hover:bg-brand-700 text-white px-3 py-1.5 rounded-lg disabled:opacity-60 transition-colors"
        >
          {uploading ? "Subiendo..." : "+ Agregar imágenes"}
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          multiple
          onChange={handleUpload}
          className="hidden"
        />
      </div>

      {error && (
        <p className="text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg px-3 py-2">
          {error}
        </p>
      )}

      <p className="text-xs text-brand-400">
        Arrastra para reordenar. Formatos: JPG, PNG, WebP. Máx. 5 MB por imagen.
      </p>

      {images.length === 0 ? (
        <div
          className="border-2 border-dashed border-brand-200 rounded-xl p-8 text-center text-brand-400 text-sm cursor-pointer hover:border-brand-400 transition-colors"
          onClick={() => fileInputRef.current?.click()}
        >
          No hay imágenes. Haz clic para subir.
        </div>
      ) : (
        <div className="grid grid-cols-3 sm:grid-cols-4 gap-3">
          {images.map((img) => (
            <div
              key={img.id}
              draggable
              onDragStart={() => handleDragStart(img.id)}
              onDragOver={(e) => handleDragOver(e, img.id)}
              onDrop={handleDrop}
              className={`relative group rounded-xl overflow-hidden border-2 cursor-move transition-all ${
                img.is_primary ? "border-brand-500 shadow-md" : "border-brand-100"
              } ${dragging === img.id ? "opacity-50" : ""}`}
            >
              <div className="aspect-square relative">
                <Image
                  src={img.url}
                  alt={img.alt_text ?? "Imagen de producto"}
                  fill
                  className="object-cover"
                  sizes="120px"
                />
              </div>
              {img.is_primary && (
                <span className="absolute top-1 left-1 bg-brand-600 text-white text-xs px-1.5 py-0.5 rounded">
                  Principal
                </span>
              )}
              <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col items-center justify-center gap-1 p-1">
                {!img.is_primary && (
                  <button
                    type="button"
                    onClick={() => handleSetPrimary(img.id)}
                    className="text-xs bg-brand-500 text-white px-2 py-1 rounded w-full"
                  >
                    Principal
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => handleDelete(img.id)}
                  className="text-xs bg-red-500 text-white px-2 py-1 rounded w-full"
                >
                  Eliminar
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
