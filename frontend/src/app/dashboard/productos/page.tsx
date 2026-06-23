"use client";

import { useEffect, useState } from "react";
import { Package, Plus, Search, Pencil, PowerOff, Download } from "lucide-react";
import { productsService } from "@/services/products.service";
import { formatCurrency } from "@/lib/formatters";
import { Modal } from "@/components/ui/Modal";
import { ProductForm } from "@/components/products/ProductForm";
import { Button } from "@/components/ui/Button";
import type { Product } from "@/types";

export default function ProductosPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Product | null>(null);

  const load = () => {
    setLoading(true);
    productsService
      .list({ active_only: false, limit: 200 })
      .then((res) => { setProducts(res.items); setTotal(res.total); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const filtered = products.filter(
    (p) =>
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.sku.toLowerCase().includes(search.toLowerCase())
  );

  const handleSuccess = (p: Product) => {
    setModalOpen(false);
    setEditing(null);
    load();
  };

  const handleToggleActive = async (p: Product) => {
    const action = p.is_active ? "desactivar" : "activar";
    if (!confirm(`¿${action} el producto "${p.name}"?`)) return;
    await productsService.update(p.id, { is_active: !p.is_active });
    load();
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Productos</h1>
          <p className="text-sm text-gray-500 mt-0.5">{total} productos en catálogo</p>
        </div>
        <div className="flex gap-2">
          <a
            href={`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/exports/products/excel`}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50 text-gray-600 transition-colors"
          >
            <Download size={14} /> Excel
          </a>
          <Button onClick={() => { setEditing(null); setModalOpen(true); }}>
            <Plus size={16} className="mr-1.5" />
            Nuevo producto
          </Button>
        </div>
      </div>

      <div className="relative mb-4 max-w-sm">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          placeholder="Buscar por nombre o SKU…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-9 pr-4 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-400"
        />
      </div>

      {loading && <p className="text-sm text-gray-500">Cargando…</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}

      {!loading && !error && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">SKU</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Nombre</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Categoría</th>
                <th className="text-right px-4 py-3 font-medium text-gray-600">Precio retail</th>
                <th className="text-right px-4 py-3 font-medium text-gray-600">P. mayorista</th>
                <th className="text-right px-4 py-3 font-medium text-gray-600">Stock</th>
                <th className="text-center px-4 py-3 font-medium text-gray-600">Estado</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-gray-400">
                    <Package size={24} className="mx-auto mb-2 opacity-40" />
                    Sin productos
                  </td>
                </tr>
              )}
              {filtered.map((p) => (
                <tr key={p.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">{p.sku}</td>
                  <td className="px-4 py-3 font-medium text-gray-900">{p.name}</td>
                  <td className="px-4 py-3 text-gray-600">{p.category_name}</td>
                  <td className="px-4 py-3 text-right">{formatCurrency(p.base_price)}</td>
                  <td className="px-4 py-3 text-right text-gray-500">
                    {p.wholesale_price ? formatCurrency(p.wholesale_price) : "—"}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className={p.quantity_on_hand !== null && p.quantity_on_hand <= 0 ? "text-red-600 font-semibold" : "text-gray-900"}>
                      {p.quantity_on_hand !== null ? `${p.quantity_on_hand} ${p.unit}` : "—"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${p.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                      {p.is_active ? "Activo" : "Inactivo"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => { setEditing(p); setModalOpen(true); }}
                        className="p-1.5 text-gray-400 hover:text-brand-600 transition-colors rounded"
                        title="Editar"
                      >
                        <Pencil size={14} />
                      </button>
                      <button
                        onClick={() => handleToggleActive(p)}
                        className={`p-1.5 transition-colors rounded ${p.is_active ? "text-gray-400 hover:text-red-500" : "text-gray-400 hover:text-green-600"}`}
                        title={p.is_active ? "Desactivar" : "Activar"}
                      >
                        <PowerOff size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal
        open={modalOpen}
        onClose={() => { setModalOpen(false); setEditing(null); }}
        title={editing ? "Editar producto" : "Nuevo producto"}
      >
        <ProductForm
          product={editing ?? undefined}
          onSuccess={handleSuccess}
          onCancel={() => { setModalOpen(false); setEditing(null); }}
        />
      </Modal>
    </div>
  );
}
