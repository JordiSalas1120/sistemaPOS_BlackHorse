import { catalogService } from "@/services/catalog.service";
import { formatCurrency } from "@/lib/formatters";
import { getModelo, getComponentes, getSpecs } from "@/lib/catalog-attributes";
import { PrintButton } from "@/components/catalog/PrintButton";
import styles from "./revista.module.css";

// Render bajo demanda (no prerenderizar en build): la revista refleja el
// catálogo actual y evita el fetch al backend durante el build de Docker.
export const dynamic = "force-dynamic";

const SHOW_PRICE = process.env.CATALOG_SHOW_PRICES !== "false";
const CURRENCY = process.env.CATALOG_CURRENCY_SYMBOL ?? "Bs.";
const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function price(n: number) {
  return `${CURRENCY} ${formatCurrency(n).replace("Bs.", "").trim()}`;
}

export default async function RevistaPage() {
  const { items: products } = await catalogService.listProducts({ limit: 100 });
  const year = new Date().getFullYear();
  const qrSrc = `${API}/api/v1/catalog/qr?path=/catalogo`;

  return (
    <div className={styles.viewport}>
      {/* Barra de herramientas — solo en pantalla */}
      <div className={styles.toolbar}>
        <a href="/catalogo" className={styles.toolbarLink}>
          ← Volver al catálogo
        </a>
        <span className={`${styles.toolbarBrand} ${styles.serif}`}>
          Black Horse · Catálogo {year}
        </span>
        <PrintButton />
      </div>

      <div className={styles.magazine}>
        {/* ── Portada ── */}
        <section className={`${styles.page} ${styles.cover}`}>
          <div className={styles.coverGrain} />
          <div className={styles.coverEyebrow}>
            Talabartería · Est. 1985 · Santa Cruz, Bolivia
          </div>
          <div>
            <h1 className={`${styles.coverTitle} ${styles.serif}`}>
              Black<span>Horse</span>
            </h1>
            <div className={styles.coverRule} />
            <p className={`${styles.coverSubtitle} ${styles.serif}`}>
              Monturas y talabartería artesanal en cuero. Edición {year}.
            </p>
          </div>
          <div className={styles.coverFooter}>
            <div className={styles.coverMeta}>
              {products.length} piezas en catálogo
              <br />
              Hecho a mano en Bolivia
            </div>
            <div className={styles.coverQr}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={qrSrc} alt="QR del catálogo en línea" />
              Escaneá para verlo en línea
            </div>
          </div>
        </section>

        {/* ── Spreads de producto ── */}
        {products.map((p, i) => {
          const img = p.images.find((x) => x.is_primary) ?? p.images[0] ?? null;
          const modelo = getModelo(p);
          const componentes = getComponentes(p);
          const specs = getSpecs(p);
          const reverse = i % 2 === 1;
          return (
            <section
              key={p.id}
              className={`${styles.page} ${styles.spread} ${reverse ? styles.spreadReverse : ""}`}
            >
              <div className={styles.photoWrap}>
                {img ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={img.url} alt={img.alt_text ?? p.name} />
                ) : (
                  <div className={styles.photoEmpty}>✦</div>
                )}
              </div>
              <div className={styles.column}>
                <div className={`${styles.folio} ${styles.serif}`}>
                  {String(i + 1).padStart(2, "0")}
                </div>
                <div className={styles.eyebrow}>{p.category_name}</div>
                <h2 className={`${styles.name} ${styles.serif}`}>{p.name}</h2>
                {modelo && <div className={`${styles.modelo} ${styles.serif}`}>{modelo}</div>}
                <div className={styles.rule} />

                {specs.length > 0 && (
                  <>
                    <div className={styles.compTitle}>Ficha técnica</div>
                    <dl className={styles.specs}>
                      {specs.map(([label, value]) => (
                        <div key={label} className={styles.specRow}>
                          <dt className={styles.specKey}>{label}</dt>
                          <dd className={styles.specVal}>{value}</dd>
                        </div>
                      ))}
                    </dl>
                  </>
                )}

                {componentes.length > 0 && (
                  <>
                    <div className={styles.compTitle}>Componentes</div>
                    <ul className={styles.compList}>
                      {componentes.map((c) => (
                        <li key={c} className={styles.compItem}>
                          {c}
                        </li>
                      ))}
                    </ul>
                  </>
                )}

                {p.description && <p className={styles.desc}>{p.description}</p>}

                <div className={styles.priceRow}>
                  {SHOW_PRICE && p.base_price != null ? (
                    <span className={`${styles.price} ${styles.serif}`}>{price(p.base_price)}</span>
                  ) : (
                    <span className={styles.modelo}>Consultar precio</span>
                  )}
                  <span className={styles.sku}>SKU {p.sku}</span>
                </div>
              </div>
            </section>
          );
        })}

        {/* ── Contraportada ── */}
        <section className={`${styles.page} ${styles.back}`}>
          <div className={styles.coverEyebrow}>Black Horse Talabartería</div>
          <h2 className={`${styles.name} ${styles.serif}`} style={{ color: "#fdf8f0" }}>
            Consultá por tu montura
          </h2>
          <p className={styles.coverSubtitle} style={{ maxWidth: "32ch" }}>
            Cada pieza es única y hecha a mano. Escribinos por WhatsApp para precios
            por cantidad y encargos a medida.
          </p>
          <div className={styles.coverQr} style={{ color: "#c9a878" }}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={qrSrc} alt="QR del catálogo en línea" />
            blackhorse.bo/catalogo
          </div>
        </section>
      </div>
    </div>
  );
}
