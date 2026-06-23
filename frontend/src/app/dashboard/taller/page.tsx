"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { WorkshopProduct } from "@/types/workshop";
import { workshopService } from "@/services/workshop.service";
import { BOMEditor } from "@/components/workshop/BOMEditor";
import { formatCurrency } from "@/lib/formatters";

type Tab = "materials" | "finished";

export default function TallerPage() {
  const [activeTab, setActiveTab] = useState<Tab>("materials");
  const [search, setSearch] = useState("");
  const [selectedProduct, setSelectedProduct] = useState<WorkshopProduct | null>(null);
  const [showBOMEditor, setShowBOMEditor] = useState(false);
  const router = useRouter();

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-brand-900">Módulo Taller</h1>
          <p className="text-brand-600 text-sm mt-1">
            Gestión de materias primas y recetas de producción
          </p>
        </div>
        <button
          onClick={() => router.push("/dashboard/taller/ordenes")}
          className="px-4 py-2 border border-brand-300 text-brand-700 rounded-md text-sm hover:bg-brand-50"
        >
          Órdenes de producción →
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-brand-200">
        {[
          { id: "materials" as Tab, label: "Materias Primas" },
          { id: "finished" as Tab, label: "Productos Terminados" },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.id
                ? "border-brand-700 text-brand-900"
                : "border-transparent text-brand-500 hover:text-brand-700"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Filtros */}
      <div className="flex gap-3 items-center">
        <input
          type="text"
          placeholder="Buscar por nombre o SKU..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="border border-brand-300 rounded-md px-3 py-2 text-sm w-64 focus:ring-brand-500"
        />
        <button
          onClick={() => router.push("/dashboard/productos")}
          className="ml-auto px-4 py-2 bg-brand-700 text-white rounded-md text-sm hover:bg-brand-800"
        >
          + Nuevo producto
        </button>
      </div>

      {/* Contenido según tab */}
      {activeTab === "materials" ? (
        <WorkshopTable kind="materials" search={search} />
      ) : (
        <WorkshopTable
          kind="finished"
          search={search}
          onEditBOM={(product) => {
            setSelectedProduct(product);
            setShowBOMEditor(true);
          }}
        />
      )}

      {/* Modal BOM Editor */}
      {showBOMEditor && selectedProduct && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl w-full max-w-4xl max-h-[90vh] overflow-y-auto">
            <BOMEditor
              product={selectedProduct}
              onClose={() => setShowBOMEditor(false)}
              onSaved={() => setShowBOMEditor(false)}
            />
          </div>
        </div>
      )}
    </div>
  );
}

interface WorkshopTableProps {
  kind: "materials" | "finished";
  search: string;
  onEditBOM?: (product: WorkshopProduct) => void;
}

function WorkshopTable({ kind, search, onEditBOM }: WorkshopTableProps) {
  const [items, setItems] = useState<WorkshopProduct[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const fetcher =
      kind === "materials"
        ? workshopService.listMaterials({ search, limit: 100 })
        : workshopService.listFinishedProducts({ search, limit: 100 });
    fetcher
      .then((res) => {
        if (!cancelled) setItems(res.items);
      })
      .catch(() => {
        if (!cancelled) setItems([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [kind, search]);

  if (loading) {
    return <p className="text-sm text-brand-500">Cargando…</p>;
  }

  if (items.length === 0) {
    return (
      <p className="text-sm text-brand-500 bg-brand-50 border border-brand-100 rounded-lg px-4 py-6 text-center">
        No hay {kind === "materials" ? "materias primas" : "productos terminados"} registrados.
        {" "}Crea productos con el tipo correspondiente desde la sección Productos.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto border border-brand-100 rounded-lg">
      <table className="w-full text-sm">
        <thead className="bg-brand-50 text-brand-700 text-left">
          <tr>
            <th className="px-4 py-2 font-medium">SKU</th>
            <th className="px-4 py-2 font-medium">Nombre</th>
            <th className="px-4 py-2 font-medium">{kind === "materials" ? "Costo" : "Precio"}</th>
            <th className="px-4 py-2 font-medium">Stock</th>
            <th className="px-4 py-2 font-medium">Unidad</th>
            {kind === "finished" && <th className="px-4 py-2 font-medium">Receta</th>}
          </tr>
        </thead>
        <tbody>
          {items.map((p) => (
            <tr key={p.id} className="border-t border-brand-100">
              <td className="px-4 py-2 font-mono text-xs text-brand-600">{p.sku}</td>
              <td className="px-4 py-2 font-medium text-brand-900">{p.name}</td>
              <td className="px-4 py-2 text-brand-700">
                {kind === "materials"
                  ? formatCurrency(p.cost_price ?? p.base_price)
                  : formatCurrency(p.base_price)}
              </td>
              <td className="px-4 py-2 text-brand-600">
                {p.quantity_on_hand != null ? `${p.quantity_on_hand}` : "—"}
              </td>
              <td className="px-4 py-2 text-brand-500">{p.unit}</td>
              {kind === "finished" && (
                <td className="px-4 py-2">
                  <button
                    onClick={() => onEditBOM?.(p)}
                    className="px-3 py-1 text-xs bg-brand-100 text-brand-800 rounded hover:bg-brand-200"
                  >
                    Ver / Crear receta
                  </button>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
