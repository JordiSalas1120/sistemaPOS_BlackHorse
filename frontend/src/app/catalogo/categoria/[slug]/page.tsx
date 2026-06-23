import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { catalogService } from "@/services/catalog.service";
import { ProductCard } from "@/components/catalog/ProductCard";

const SHOW_PRICE = process.env.CATALOG_SHOW_PRICES !== "false";
const CURRENCY = process.env.CATALOG_CURRENCY_SYMBOL ?? "Bs.";

interface PageProps {
  params: { slug: string };
  searchParams: { pagina?: string };
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const categories = await catalogService.listCategories();
  const cat = categories.find((c) => c.slug === params.slug);
  if (!cat) return { title: "Categoría no encontrada" };
  return {
    title: `${cat.name} — Catálogo`,
    description: cat.description ?? `Productos de ${cat.name} en cuero artesanal.`,
    openGraph: { title: `${cat.name} | Black Horse Talabartería` },
  };
}

export default async function CategoriaPage({ params, searchParams }: PageProps) {
  const LIMIT = 24;
  const page = Number(searchParams.pagina ?? 1);
  const skip = (page - 1) * LIMIT;

  const [{ items: products, total }, categories] = await Promise.all([
    catalogService.listProducts({ category_slug: params.slug, skip, limit: LIMIT }),
    catalogService.listCategories(),
  ]);

  const category = categories.find((c) => c.slug === params.slug);
  if (!category) notFound();

  return (
    <div>
      <div className="mb-8">
        <nav className="text-sm text-brand-400 mb-2">
          <a href="/catalogo" className="hover:text-brand-600">
            Catálogo
          </a>{" "}
          / {category.name}
        </nav>
        <h1 className="text-3xl font-bold text-brand-900">{category.name}</h1>
        {category.description && <p className="text-brand-500 mt-2">{category.description}</p>}
        <p className="text-brand-400 text-sm mt-1">{total} productos</p>
      </div>

      {products.length === 0 ? (
        <p className="text-center text-brand-400 py-20">No hay productos en esta categoría.</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {products.map((p) => (
            <ProductCard key={p.id} product={p} showPrice={SHOW_PRICE} currencySymbol={CURRENCY} />
          ))}
        </div>
      )}
    </div>
  );
}
