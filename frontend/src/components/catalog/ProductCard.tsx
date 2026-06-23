import Image from "next/image";
import Link from "next/link";
import type { CatalogProduct } from "@/types/catalog";
import { formatCurrency } from "@/lib/formatters";

interface ProductCardProps {
  product: CatalogProduct;
  showPrice: boolean;
  currencySymbol: string;
}

const LEATHER_PLACEHOLDER =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='400' viewBox='0 0 400 400'%3E%3Crect width='400' height='400' fill='%23d4a574'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' font-family='serif' font-size='60' fill='%23a0522d'%3E%F0%9F%A7%B5%3C/text%3E%3C/svg%3E";

const WA_PHONE = process.env.NEXT_PUBLIC_WHATSAPP_PHONE ?? "591XXXXXXXXX";

export function ProductCard({ product, showPrice, currencySymbol }: ProductCardProps) {
  const primaryImage =
    product.images.find((img) => img.is_primary) ?? product.images[0] ?? null;

  return (
    <div className="bg-white rounded-2xl shadow-sm hover:shadow-md transition-shadow overflow-hidden group border border-brand-100">
      {/* Imagen */}
      <div className="relative aspect-square overflow-hidden bg-brand-50">
        <Image
          src={primaryImage?.url ?? LEATHER_PLACEHOLDER}
          alt={primaryImage?.alt_text ?? product.name}
          fill
          className="object-cover group-hover:scale-105 transition-transform duration-300"
          sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
          unoptimized={!primaryImage}
        />
        <span className="absolute top-3 left-3 bg-brand-800/80 text-white text-xs font-medium px-2 py-1 rounded-full backdrop-blur-sm">
          {product.category_name}
        </span>
        <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
          <a
            href={`https://wa.me/${WA_PHONE}?text=${encodeURIComponent(
              `Hola, me interesa ${product.name} (SKU: ${product.sku})`,
            )}`}
            target="_blank"
            rel="noopener noreferrer"
            className="bg-green-500 hover:bg-green-600 text-white text-sm font-semibold px-4 py-2 rounded-full"
          >
            Consultar
          </a>
        </div>
      </div>

      {/* Info */}
      <div className="p-4">
        <h3 className="font-semibold text-brand-900 text-sm leading-tight line-clamp-2 mb-1">
          {product.name}
        </h3>
        <p className="text-brand-400 text-xs mb-3">SKU: {product.sku}</p>

        {showPrice && product.base_price != null && (
          <p className="text-brand-700 font-bold text-lg">
            {currencySymbol} {formatCurrency(product.base_price).replace("Bs.", "").trim()}
          </p>
        )}

        <Link
          href={`/catalogo/${product.sku}`}
          className="mt-3 block text-center bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium py-2 px-4 rounded-lg transition-colors"
        >
          Ver detalle
        </Link>
      </div>
    </div>
  );
}
