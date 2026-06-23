"use client";

import { useState } from "react";
import Image from "next/image";
import type { CatalogImage } from "@/types/catalog";

const PLACEHOLDER =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='800' height='800' viewBox='0 0 800 800'%3E%3Crect width='800' height='800' fill='%23d4a574'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' font-size='120' fill='%23a0522d'%3E%F0%9F%A7%B5%3C/text%3E%3C/svg%3E";

interface ImageGalleryProps {
  images: CatalogImage[];
  productName: string;
}

export function ImageGallery({ images, productName }: ImageGalleryProps) {
  const [activeIndex, setActiveIndex] = useState(0);

  const sorted = [...images].sort((a, b) => {
    if (a.is_primary && !b.is_primary) return -1;
    if (!a.is_primary && b.is_primary) return 1;
    return a.sort_order - b.sort_order;
  });

  const activeImage = sorted[activeIndex] ?? null;

  return (
    <div className="flex flex-col gap-4">
      {/* Imagen principal */}
      <div className="relative aspect-square rounded-2xl overflow-hidden bg-brand-50 border border-brand-100">
        <Image
          src={activeImage?.url ?? PLACEHOLDER}
          alt={activeImage?.alt_text ?? productName}
          fill
          priority
          className="object-cover"
          sizes="(max-width: 1024px) 100vw, 50vw"
          unoptimized={!activeImage}
        />
      </div>

      {/* Miniaturas */}
      {sorted.length > 1 && (
        <div className="flex gap-3 overflow-x-auto pb-1">
          {sorted.map((img, index) => (
            <button
              key={img.id}
              onClick={() => setActiveIndex(index)}
              className={`relative flex-shrink-0 w-20 h-20 rounded-lg overflow-hidden border-2 transition-all ${
                index === activeIndex
                  ? "border-brand-600 shadow-md"
                  : "border-brand-200 opacity-70 hover:opacity-100"
              }`}
              aria-label={`Ver imagen ${index + 1}`}
              aria-current={index === activeIndex}
            >
              <Image
                src={img.url}
                alt={img.alt_text ?? `${productName} imagen ${index + 1}`}
                fill
                className="object-cover"
                sizes="80px"
              />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
