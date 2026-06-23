import Link from "next/link";
import type { CatalogCategory } from "@/types/catalog";

interface CategoryFilterProps {
  categories: CatalogCategory[];
  activeSlug?: string;
}

export function CategoryFilter({ categories, activeSlug }: CategoryFilterProps) {
  return (
    <ul className="space-y-1">
      <li>
        <Link
          href="/catalogo"
          className={`flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors ${
            !activeSlug
              ? "bg-brand-100 text-brand-900 font-semibold"
              : "text-brand-600 hover:bg-brand-50"
          }`}
        >
          <span>Todos</span>
        </Link>
      </li>
      {categories.map((cat) => (
        <li key={cat.id}>
          <Link
            href={`/catalogo?categoria=${cat.slug}`}
            className={`flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors ${
              activeSlug === cat.slug
                ? "bg-brand-100 text-brand-900 font-semibold"
                : "text-brand-600 hover:bg-brand-50"
            }`}
          >
            <span>{cat.name}</span>
            <span className="bg-brand-200 text-brand-700 text-xs px-2 py-0.5 rounded-full">
              {cat.product_count}
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
