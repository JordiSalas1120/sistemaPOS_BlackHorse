import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { catalogService } from "@/services/catalog.service";
import { WhatsAppButton } from "@/components/catalog/WhatsAppButton";
import { ImageGallery } from "@/components/catalog/ImageGallery";
import { ProductCard } from "@/components/catalog/ProductCard";
import { SharePanel } from "@/components/catalog/SharePanel";
import { formatCurrency } from "@/lib/formatters";
import { getModelo, getComponentes, getExtraAttributes } from "@/lib/catalog-attributes";
import type { CatalogProduct } from "@/types/catalog";

const SHOW_PRICE = process.env.CATALOG_SHOW_PRICES !== "false";
const CURRENCY = process.env.CATALOG_CURRENCY_SYMBOL ?? "Bs.";
const WA_PHONE = process.env.NEXT_PUBLIC_WHATSAPP_PHONE ?? "591XXXXXXXXX";
const WA_TEMPLATE =
  process.env.NEXT_PUBLIC_WHATSAPP_TEMPLATE ??
  "Hola, me interesa el producto *{product_name}* (SKU: {sku}). ¿Podría darme más información?";

interface PageProps {
  params: { sku: string };
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  try {
    const product = await catalogService.getProductBySku(params.sku.toUpperCase());
    const primaryImage = product.images.find((img) => img.is_primary) ?? product.images[0];
    const description =
      product.description ??
      `${product.name} — ${product.category_name}. Artículo de cuero artesanal.`;

    return {
      title: product.name,
      description,
      openGraph: {
        title: `${product.name} | Black Horse Talabartería`,
        description,
        type: "website",
        images: primaryImage
          ? [{ url: primaryImage.url, width: 800, height: 800, alt: primaryImage.alt_text ?? product.name }]
          : [],
      },
    };
  } catch {
    return { title: "Producto no encontrado" };
  }
}

export default async function ProductoDetallePage({ params }: PageProps) {
  let product: CatalogProduct;
  try {
    product = await catalogService.getProductBySku(params.sku.toUpperCase());
  } catch {
    notFound();
  }

  const relatedProducts = await catalogService.getRelatedProducts(product.sku);

  const attributeLabels: Record<string, string> = {
    leather_type: "Tipo de cuero",
    color: "Color",
    size: "Talla / Medida",
    weight_kg: "Peso (kg)",
    talla: "Talla",
    acabado: "Acabado",
    origin: "Origen",
  };

  const modelo = getModelo(product);
  const componentes = getComponentes(product);
  const attributeEntries = getExtraAttributes(product);

  return (
    <>
      <WhatsAppButton
        productName={product.name}
        sku={product.sku}
        phoneNumber={WA_PHONE}
        messageTemplate={WA_TEMPLATE}
        variant="fixed"
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
        <ImageGallery images={product.images} productName={product.name} />

        <div className="flex flex-col gap-6">
          <nav className="text-sm text-brand-400">
            <a href="/catalogo" className="hover:text-brand-600 transition-colors">
              Catálogo
            </a>
            {" / "}
            <a
              href={`/catalogo?categoria=${product.category_slug}`}
              className="hover:text-brand-600 transition-colors"
            >
              {product.category_name}
            </a>
            {" / "}
            <span className="text-brand-700">{product.name}</span>
          </nav>

          <div>
            <span className="bg-brand-100 text-brand-700 text-xs font-medium px-2 py-1 rounded-full">
              {product.category_name}
            </span>
            <h1 className="text-3xl font-bold text-brand-900 mt-3 leading-tight">
              {product.name}
            </h1>
            {modelo && <p className="text-brand-600 italic mt-1">{modelo}</p>}
            <p className="text-brand-400 text-sm mt-1">SKU: {product.sku}</p>
          </div>

          {componentes.length > 0 && (
            <div>
              <h2 className="font-semibold text-brand-800 mb-2">Características y componentes</h2>
              <div className="flex flex-wrap gap-2">
                {componentes.map((c) => (
                  <span
                    key={c}
                    className="inline-flex items-center gap-1.5 rounded-full bg-brand-50 border border-brand-200 px-3 py-1 text-sm text-brand-800"
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-brand-500" />
                    {c}
                  </span>
                ))}
              </div>
            </div>
          )}

          {SHOW_PRICE && product.base_price != null && (
            <div className="bg-brand-50 border border-brand-200 rounded-xl p-4">
              <p className="text-brand-500 text-sm mb-1">Precio</p>
              <p className="text-4xl font-bold text-brand-800">
                {CURRENCY} {formatCurrency(product.base_price).replace("Bs.", "").trim()}
              </p>
              <p className="text-brand-400 text-xs mt-1">
                Precio en {product.unit}. Consultar por cantidad.
              </p>
            </div>
          )}

          {product.description && (
            <div>
              <h2 className="font-semibold text-brand-800 mb-2">Descripción</h2>
              <p className="text-brand-600 leading-relaxed">{product.description}</p>
            </div>
          )}

          {attributeEntries.length > 0 && (
            <div>
              <h2 className="font-semibold text-brand-800 mb-3">Características</h2>
              <table className="w-full text-sm border-collapse">
                <tbody>
                  {attributeEntries.map(([key, value]) => (
                    <tr key={key} className="border-b border-brand-100">
                      <td className="py-2 pr-4 text-brand-500 font-medium w-40">
                        {attributeLabels[key] ?? key}
                      </td>
                      <td className="py-2 text-brand-800">{String(value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="hidden sm:flex items-center gap-3 flex-wrap">
            <WhatsAppButton
              productName={product.name}
              sku={product.sku}
              phoneNumber={WA_PHONE}
              messageTemplate={WA_TEMPLATE}
              variant="inline"
            />
            <SharePanel
              path={`/catalogo/${product.sku}`}
              message={`Mirá esta pieza de Black Horse: ${product.name}`}
            />
          </div>

          <p className="text-brand-400 text-xs">
            Horario de atención: Lunes a Sábado 8:00 – 18:00 hs.
          </p>
        </div>
      </div>

      {relatedProducts.length > 0 && (
        <section className="mt-16">
          <h2 className="text-2xl font-bold text-brand-900 mb-6">También te puede interesar</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {relatedProducts.map((p) => (
              <ProductCard key={p.id} product={p} showPrice={SHOW_PRICE} currencySymbol={CURRENCY} />
            ))}
          </div>
        </section>
      )}
    </>
  );
}
