"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useTransition } from "react";

export function CatalogSearch() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();

  const handleSearch = useCallback(
    (value: string) => {
      const params = new URLSearchParams(searchParams.toString());
      if (value) {
        params.set("buscar", value);
      } else {
        params.delete("buscar");
      }
      params.delete("pagina"); // reset paginación al buscar
      startTransition(() => {
        router.push(`/catalogo?${params.toString()}`);
      });
    },
    [router, searchParams],
  );

  return (
    <div className="relative">
      <input
        type="search"
        placeholder="Buscar productos..."
        defaultValue={searchParams.get("buscar") ?? ""}
        onChange={(e) => handleSearch(e.target.value)}
        className={`w-full border border-brand-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400 bg-brand-50 ${
          isPending ? "opacity-70" : ""
        }`}
        aria-label="Buscar en el catálogo"
      />
    </div>
  );
}
