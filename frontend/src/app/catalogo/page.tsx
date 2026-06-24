import type { Metadata } from "next";
import { Suspense } from "react";
import Link from "next/link";
import { catalogService } from "@/services/catalog.service";
import { ProductCard } from "@/components/catalog/ProductCard";
import { CategoryFilter } from "@/components/catalog/CategoryFilter";
import { CatalogSearch } from "@/components/catalog/CatalogSearch";
import { SharePanel } from "@/components/catalog/SharePanel";

export const metadata: Metadata = {
  title: "Catálogo de Productos",
  description:
    "Explora nuestra colección de artículos de cuero artesanales: monturas, riendas, accesorios equinos, bovinos y marroquinería.",
  openGraph: {
    title: "Catálogo | Black Horse Talabartería",
    description: "Artículos de cuero artesanales desde Bolivia.",
    type: "website",
  },
};

interface PageProps {
  searchParams: {
    categoria?: string;
    buscar?: string;
    pagina?: string;
  };
}

const LIMIT = 24;
const SHOW_PRICE = process.env.CATALOG_SHOW_PRICES !== "false";
const CURRENCY = process.env.CATALOG_CURRENCY_SYMBOL ?? "Bs.";

export default async function CatalogoPage({ searchParams }: PageProps) {
  const page = Number(searchParams.pagina ?? 1);
  const skip = (page - 1) * LIMIT;

  const [{ items: products, total }, categories] = await Promise.all([
    catalogService.listProducts({
      category_slug: searchParams.categoria,
      search: searchParams.buscar,
      skip,
      limit: LIMIT,
    }),
    catalogService.listCategories(),
  ]);

  const totalPages = Math.ceil(total / LIMIT);

  return (
    <>
      {/* Banda editorial: acceso a la revista + compartir */}
      <div className="mb-8 rounded-2xl bg-gradient-to-r from-brand-800 to-brand-900 text-white p-6 sm:p-8 flex flex-col sm:flex-row sm:items-center justify-between gap-5 overflow-hidden">
        <div>
          <p className="text-brand-300 text-[0.7rem] uppercase tracking-[0.3em] mb-1">
            Black Horse · Talabartería
          </p>
          <h1 className="text-2xl sm:text-3xl font-bold leading-tight">
            Catálogo de monturas &amp; cuero
          </h1>
          <p className="text-brand-200 text-sm mt-1">
            Piezas artesanales hechas a mano. Mirá la versión revista o descargala en PDF.
          </p>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <Link
            href="/revista"
            className="inline-flex items-center gap-2 rounded-full bg-brand-500 hover:bg-brand-400 text-white px-5 py-2.5 text-sm font-semibold transition-colors"
          >
            Ver catálogo revista
          </Link>
          <SharePanel
            path="/catalogo"
            message="Mirá el catálogo de Black Horse Talabartería:"
          />
        </div>
      </div>

      <div className="flex flex-col lg:flex-row gap-8">
      {/* Sidebar filtros */}
      <aside className="w-full lg:w-64 flex-shrink-0">
        <div className="bg-white rounded-2xl shadow-sm border border-brand-100 p-5 lg:sticky lg:top-4">
          <h2 className="font-bold text-brand-900 mb-4 text-lg">Filtros</h2>
          <Suspense>
            <CatalogSearch />
          </Suspense>
          <div className="mt-6">
            <h3 className="font-semibold text-brand-700 mb-3 text-sm uppercase tracking-wide">
              Categorías
            </h3>
            <CategoryFilter categories={categories} activeSlug={searchParams.categoria} />
          </div>
        </div>
      </aside>

      {/* Grid de productos */}
      <section className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-6">
          <p className="text-brand-500 text-sm">
            {total} {total === 1 ? "producto" : "productos"}
            {searchParams.categoria && ` en ${searchParams.categoria}`}
          </p>
        </div>

        {products.length === 0 ? (
          <div className="text-center py-20 text-brand-400">
            <p className="text-2xl mb-2">No hay productos disponibles</p>
            <p className="text-sm">Intenta con otros filtros o categorías.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-6">
            {products.map((product) => (
              <ProductCard
                key={product.id}
                product={product}
                showPrice={SHOW_PRICE}
                currencySymbol={CURRENCY}
              />
            ))}
          </div>
        )}

        {/* Paginación clásica (indexable por SEO) */}
        {totalPages > 1 && (
          <nav className="flex justify-center gap-2 mt-10 flex-wrap" aria-label="Paginación">
            {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
              <a
                key={p}
                href={`/catalogo?${new URLSearchParams({
                  ...(searchParams.categoria ? { categoria: searchParams.categoria } : {}),
                  ...(searchParams.buscar ? { buscar: searchParams.buscar } : {}),
                  pagina: String(p),
                })}`}
                className={`w-10 h-10 flex items-center justify-center rounded-lg text-sm font-medium transition-colors ${
                  p === page
                    ? "bg-brand-600 text-white"
                    : "bg-white text-brand-700 border border-brand-200 hover:bg-brand-50"
                }`}
                aria-current={p === page ? "page" : undefined}
              >
                {p}
              </a>
            ))}
          </nav>
        )}
      </section>
      </div>
    </>
  );
}
