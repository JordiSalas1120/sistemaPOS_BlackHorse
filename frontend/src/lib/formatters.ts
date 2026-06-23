/**
 * Formatea un número como moneda local (peso argentino por defecto).
 */
export function formatCurrency(
  amount: number | string,
  currency = "BOB",
  locale = "es-BO"
): string {
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
  }).format(Number(amount));
}

/**
 * Formatea una fecha ISO a formato legible en español.
 */
export function formatDate(
  isoString: string,
  locale = "es-BO"
): string {
  return new Intl.DateTimeFormat(locale, {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(isoString));
}
