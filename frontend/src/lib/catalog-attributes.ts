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

/** Etiquetas legibles para las claves de atributos conocidas (es-AR/es-BO). */
export const ATTRIBUTE_LABELS: Record<string, string> = {
  leather_type: "Tipo de cuero",
  cuero: "Tipo de cuero",
  material: "Material",
  color: "Color",
  size: "Talla / Medida",
  talla: "Talla",
  medida: "Medida",
  medidas: "Medidas",
  dimensiones: "Dimensiones",
  weight_kg: "Peso (kg)",
  peso: "Peso",
  peso_kg: "Peso (kg)",
  acabado: "Acabado",
  terminacion: "Terminación",
  herrajes: "Herrajes",
  costura: "Costura",
  relleno: "Relleno",
  forro: "Forro",
  origin: "Origen",
  origen: "Origen",
  garantia: "Garantía",
  uso: "Uso recomendado",
};

/** Convierte una clave sin etiqueta conocida en texto legible: "leather_type" → "Leather Type". */
function humanizeKey(key: string): string {
  return key
    .replace(/[_-]+/g, " ")
    .trim()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Etiqueta legible para una clave de atributo (usa el mapa o humaniza la clave). */
export function labelFor(key: string): string {
  return ATTRIBUTE_LABELS[key] ?? humanizeKey(key);
}

/**
 * Ficha técnica del producto: pares [etiqueta, valor] listos para mostrar,
 * como las especificaciones de un celular/computadora. Excluye modelo y componentes
 * (que tienen render dedicado) y los valores vacíos.
 */
export function getSpecs(
  p: Pick<CatalogProduct, "attributes">,
): [string, string][] {
  return getExtraAttributes(p).map(([k, v]) => [labelFor(k), v] as [string, string]);
}
