import type { CatalogProduct } from "@/types/catalog";

/** Modelo editorial del producto (ej. "Montura Beniana"), guardado en attributes.modelo. */
export function getModelo(p: Pick<CatalogProduct, "attributes">): string | null {
  const m = (p.attributes ?? {})["modelo"];
  return typeof m === "string" && m.trim() ? m.trim() : null;
}

/** Componentes/partes del producto (estribos, caronas, manta, colcha…). */
export function getComponentes(p: Pick<CatalogProduct, "attributes">): string[] {
  const c = (p.attributes ?? {})["componentes"];
  if (Array.isArray(c)) return c.map((x) => String(x).trim()).filter(Boolean);
  if (typeof c === "string") {
    return c
      .split(/[\n,]/)
      .map((s) => s.trim())
      .filter(Boolean);
  }
  return [];
}

/** Resto de atributos (excluye los que tienen render dedicado). */
const RESERVED = new Set(["modelo", "componentes"]);
export function getExtraAttributes(
  p: Pick<CatalogProduct, "attributes">,
): [string, string][] {
  return Object.entries(p.attributes ?? {})
    .filter(([k, v]) => !RESERVED.has(k) && v !== null && v !== undefined && v !== "")
    .map(([k, v]) => [k, String(v)] as [string, string]);
}
