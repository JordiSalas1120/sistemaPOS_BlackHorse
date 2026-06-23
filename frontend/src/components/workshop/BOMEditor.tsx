"use client";

import { useEffect, useRef, useState } from "react";
import { BOMItem, WorkshopProduct } from "@/types/workshop";
import { workshopService } from "@/services/workshop.service";
import { formatCurrency } from "@/lib/formatters";

interface BOMEditorProps {
  product: WorkshopProduct;      // el producto terminado dueño de la receta
  onClose: () => void;
  onSaved: () => void;
}

interface BOMEditorItem {
  materialId: string;
  materialName: string;
  materialSku: string;
  unit: string;
  unitPrice: number;      // cost_price ?? base_price
  quantityRequired: number;
  scrapFactor: number;    // 0–0.9999
  notes: string;
  effectiveQuantity: number;
  subtotal: number;
}

function mapBOMItemToEditorItem(
  item: BOMItem,
  materialNames: Record<string, string>,
): BOMEditorItem {
  return {
    materialId: item.material_id,
    materialName: materialNames[item.material_id] ?? item.material_id,
    materialSku: "",
    unit: "",
    unitPrice: 0,
    quantityRequired: item.quantity_required,
    scrapFactor: item.scrap_factor,
    notes: item.notes ?? "",
    effectiveQuantity: item.effective_quantity,
    subtotal: 0,
  };
}

export function BOMEditor({ product, onClose, onSaved }: BOMEditorProps) {
  const [items, setItems] = useState<BOMEditorItem[]>([]);
  const [outputQuantity, setOutputQuantity] = useState(1);
  const [laborMinutes, setLaborMinutes] = useState<number | null>(null);
  const [notes, setNotes] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [existingBomId, setExistingBomId] = useState<string | null>(null);

  // Cargar BOM existente al montar
  useEffect(() => {
    workshopService
      .getBOM(product.id)
      .then((bom) => {
        setExistingBomId(bom.id);
        setOutputQuantity(bom.output_quantity);
        setLaborMinutes(bom.labor_minutes ?? null);
        setNotes(bom.notes ?? "");
        // Reconstruir precios y subtotales desde el detalle de costo
        setItems(
          bom.items.map((i) => {
            const editorItem = mapBOMItemToEditorItem(i, bom.material_names);
            return editorItem;
          }),
        );
      })
      .catch(() => {
        // No existe BOM aún — editor vacío
      })
      .finally(() => setIsLoading(false));
  }, [product.id]);

  const totalCost = items.reduce((sum, i) => sum + i.subtotal, 0);
  const costPerUnit = outputQuantity > 0 ? totalCost / outputQuantity : 0;

  const handleAddMaterial = (material: WorkshopProduct) => {
    if (items.some((i) => i.materialId === material.id)) return;
    const unitPrice = material.cost_price ?? material.base_price;
    setItems((prev) => [
      ...prev,
      {
        materialId: material.id,
        materialName: material.name,
        materialSku: material.sku,
        unit: material.unit,
        unitPrice,
        quantityRequired: 1,
        scrapFactor: 0,
        notes: "",
        effectiveQuantity: 1,
        subtotal: unitPrice,
      },
    ]);
  };

  const handleItemChange = (
    index: number,
    field: "quantityRequired" | "scrapFactor" | "notes",
    value: number | string,
  ) => {
    setItems((prev) => {
      const updated = [...prev];
      const item = { ...updated[index], [field]: value };
      item.effectiveQuantity = item.quantityRequired * (1 + item.scrapFactor);
      item.subtotal = item.effectiveQuantity * item.unitPrice;
      updated[index] = item;
      return updated;
    });
  };

  const handleRemoveItem = (index: number) => {
    setItems((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSave = async () => {
    if (items.length === 0) {
      setError("La receta debe tener al menos un material.");
      return;
    }
    setIsSaving(true);
    setError(null);
    try {
      const payload = {
        output_quantity: outputQuantity,
        labor_minutes: laborMinutes ?? undefined,
        notes: notes || undefined,
        items: items.map((i) => ({
          material_id: i.materialId,
          quantity_required: i.quantityRequired,
          scrap_factor: i.scrapFactor,
          notes: i.notes || undefined,
        })),
      };

      if (existingBomId) {
        await workshopService.updateBOM(product.id, payload);
      } else {
        await workshopService.createBOM(product.id, payload);
      }
      onSaved();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al guardar la receta.");
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return <div className="p-6 text-sm text-brand-600">Cargando receta…</div>;
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-start">
        <div>
          <h2 className="text-xl font-bold text-brand-900">Receta de producción</h2>
          <p className="text-sm text-brand-600">
            {product.name} ({product.sku})
          </p>
        </div>
        <button onClick={onClose} className="text-brand-400 hover:text-brand-700 text-2xl leading-none">
          ×
        </button>
      </div>

      {/* Cabecera BOM */}
      <div className="grid grid-cols-3 gap-4">
        <div>
          <label className="text-xs font-medium text-brand-700">Cantidad producida por lote</label>
          <input
            type="number"
            min="0.001"
            step="0.001"
            value={outputQuantity}
            onChange={(e) => setOutputQuantity(parseFloat(e.target.value) || 1)}
            className="mt-1 w-full border border-brand-300 rounded px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="text-xs font-medium text-brand-700">Mano de obra (minutos)</label>
          <input
            type="number"
            min="0"
            value={laborMinutes ?? ""}
            onChange={(e) => setLaborMinutes(e.target.value ? parseInt(e.target.value) : null)}
            className="mt-1 w-full border border-brand-300 rounded px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="text-xs font-medium text-brand-700">Notas</label>
          <input
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="mt-1 w-full border border-brand-300 rounded px-3 py-2 text-sm"
          />
        </div>
      </div>

      {/* Tabla de materiales */}
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="bg-brand-50 text-brand-700 text-left">
            <th className="px-3 py-2 font-medium">Material</th>
            <th className="px-3 py-2 font-medium">Cantidad</th>
            <th className="px-3 py-2 font-medium">Desperdicio %</th>
            <th className="px-3 py-2 font-medium">Cant. efectiva</th>
            <th className="px-3 py-2 font-medium">Precio unit.</th>
            <th className="px-3 py-2 font-medium">Subtotal</th>
            <th className="px-3 py-2"></th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, idx) => (
            <tr key={item.materialId} className="border-t border-brand-100">
              <td className="px-3 py-2">
                <span className="font-medium">{item.materialName}</span>
                {item.materialSku && (
                  <span className="text-brand-400 text-xs ml-1">{item.materialSku}</span>
                )}
              </td>
              <td className="px-3 py-2">
                <input
                  type="number"
                  min="0.001"
                  step="0.001"
                  value={item.quantityRequired}
                  onChange={(e) => handleItemChange(idx, "quantityRequired", parseFloat(e.target.value) || 0)}
                  className="w-20 border border-brand-200 rounded px-2 py-1"
                />
                {item.unit && <span className="text-brand-400 text-xs ml-1">{item.unit}</span>}
              </td>
              <td className="px-3 py-2">
                <input
                  type="number"
                  min="0"
                  max="99.99"
                  step="0.01"
                  value={(item.scrapFactor * 100).toFixed(2)}
                  onChange={(e) =>
                    handleItemChange(idx, "scrapFactor", (parseFloat(e.target.value) || 0) / 100)
                  }
                  className="w-20 border border-brand-200 rounded px-2 py-1"
                />
                <span className="text-brand-400 text-xs ml-1">%</span>
              </td>
              <td className="px-3 py-2 text-brand-600">
                {item.effectiveQuantity.toFixed(3)} {item.unit}
              </td>
              <td className="px-3 py-2 text-brand-600">{formatCurrency(item.unitPrice)}</td>
              <td className="px-3 py-2 font-medium text-brand-900">{formatCurrency(item.subtotal)}</td>
              <td className="px-3 py-2">
                <button
                  onClick={() => handleRemoveItem(idx)}
                  className="text-red-400 hover:text-red-600 text-lg leading-none"
                >
                  ×
                </button>
              </td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="border-t-2 border-brand-300 bg-brand-50">
            <td colSpan={5} className="px-3 py-3 text-right font-semibold text-brand-800">
              Costo total del lote:
            </td>
            <td className="px-3 py-3 font-bold text-brand-900 text-lg">{formatCurrency(totalCost)}</td>
            <td />
          </tr>
          <tr className="bg-brand-50">
            <td colSpan={5} className="px-3 py-2 text-right text-sm text-brand-600">
              Costo por unidad ({outputQuantity} {product.unit}):
            </td>
            <td className="px-3 py-2 font-semibold text-brand-800">{formatCurrency(costPerUnit)}</td>
            <td />
          </tr>
        </tfoot>
      </table>

      {/* Buscador de materiales */}
      <MaterialSearchPanel onAdd={handleAddMaterial} excludeIds={items.map((i) => i.materialId)} />

      {error && (
        <p className="text-red-600 text-sm bg-red-50 border border-red-200 rounded px-3 py-2">{error}</p>
      )}

      <div className="flex justify-end gap-3 pt-2">
        <button onClick={onClose} className="px-4 py-2 border border-brand-300 text-brand-700 rounded-md text-sm">
          Cancelar
        </button>
        <button
          onClick={handleSave}
          disabled={isSaving}
          className="px-5 py-2 bg-brand-700 text-white rounded-md text-sm hover:bg-brand-800 disabled:opacity-50"
        >
          {isSaving ? "Guardando..." : "Guardar receta"}
        </button>
      </div>
    </div>
  );
}

interface MaterialSearchPanelProps {
  onAdd: (material: WorkshopProduct) => void;
  excludeIds: string[];
}

function MaterialSearchPanel({ onAdd, excludeIds }: MaterialSearchPanelProps) {
  const [search, setSearch] = useState("");
  const [results, setResults] = useState<WorkshopProduct[]>([]);
  const [loading, setLoading] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!search.trim()) {
      setResults([]);
      return;
    }
    debounceRef.current = setTimeout(() => {
      setLoading(true);
      workshopService
        .listMaterials({ search, limit: 10 })
        .then((res) => setResults(res.items))
        .catch(() => setResults([]))
        .finally(() => setLoading(false));
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [search]);

  const visible = results.filter((r) => !excludeIds.includes(r.id));

  return (
    <div className="border border-brand-200 rounded-lg p-4 space-y-3">
      <label className="text-sm font-medium text-brand-700">Agregar material a la receta</label>
      <input
        type="text"
        placeholder="Buscar materia prima por nombre o SKU…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="w-full border border-brand-300 rounded px-3 py-2 text-sm"
      />
      {loading && <p className="text-xs text-brand-400">Buscando…</p>}
      {!loading && search.trim() && visible.length === 0 && (
        <p className="text-xs text-brand-400">Sin resultados.</p>
      )}
      <div className="flex flex-col gap-1">
        {visible.map((material) => (
          <button
            key={material.id}
            onClick={() => {
              onAdd(material);
              setSearch("");
              setResults([]);
            }}
            className="flex justify-between items-center text-left px-3 py-2 rounded hover:bg-brand-50 text-sm"
          >
            <span>
              <span className="font-medium text-brand-900">{material.name}</span>
              <span className="text-brand-400 text-xs ml-2">{material.sku}</span>
            </span>
            <span className="text-brand-600 text-xs">
              {formatCurrency(material.cost_price ?? material.base_price)} / {material.unit}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
