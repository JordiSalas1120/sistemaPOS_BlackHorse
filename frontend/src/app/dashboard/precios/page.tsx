"use client";

import { useEffect, useState } from "react";
import { Tag, Plus, Trash2, Power } from "lucide-react";
import { priceRulesService, type PriceRule, type CreatePriceRuleInput } from "@/services/price-rules.service";
import { Modal } from "@/components/ui/Modal";
import { FormField, SelectField } from "@/components/ui/FormField";
import { Button } from "@/components/ui/Button";

const RULE_TYPE_LABELS: Record<string, string> = {
  quantity_threshold: "Cantidad mínima",
  client_type: "Tipo de cliente",
  category_discount: "Categoría",
};

const DISCOUNT_TYPE_LABELS: Record<string, string> = {
  percentage: "Porcentaje (%)",
  fixed_amount: "Monto fijo ($)",
};

export default function PreciosPage() {
  const [rules, setRules] = useState<PriceRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const [form, setForm] = useState<CreatePriceRuleInput>({
    name: "",
    rule_type: "client_type",
    discount_type: "percentage",
    discount_value: 0,
    priority: 0,
  });

  const load = () => {
    setLoading(true);
    priceRulesService
      .list()
      .then(setRules)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const handleToggle = async (rule: PriceRule) => {
    await priceRulesService.toggle(rule.id, !rule.is_active);
    load();
  };

  const handleDelete = async (rule: PriceRule) => {
    if (!confirm(`¿Eliminar la regla "${rule.name}"?`)) return;
    await priceRulesService.remove(rule.id);
    load();
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name || form.discount_value <= 0) {
      setFormError("Nombre y valor de descuento son obligatorios.");
      return;
    }
    setSaving(true);
    setFormError(null);
    try {
      await priceRulesService.create(form);
      setModalOpen(false);
      setForm({ name: "", rule_type: "client_type", discount_type: "percentage", discount_value: 0, priority: 0 });
      load();
    } catch (e: unknown) {
      setFormError(e instanceof Error ? e.message : "Error al guardar");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Reglas de precios</h1>
          <p className="text-sm text-gray-500 mt-0.5">Descuentos por volumen, tipo de cliente o categoría</p>
        </div>
        <Button onClick={() => setModalOpen(true)}>
          <Plus size={16} className="mr-1.5" />
          Nueva regla
        </Button>
      </div>

      {loading && <p className="text-sm text-gray-500">Cargando…</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}

      {!loading && !error && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Nombre</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Tipo</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Condición</th>
                <th className="text-right px-4 py-3 font-medium text-gray-600">Descuento</th>
                <th className="text-right px-4 py-3 font-medium text-gray-600">Prioridad</th>
                <th className="text-center px-4 py-3 font-medium text-gray-600">Estado</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {rules.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-gray-400">
                    <Tag size={24} className="mx-auto mb-2 opacity-40" />
                    Sin reglas de precios
                  </td>
                </tr>
              )}
              {rules.map((r) => (
                <tr key={r.id} className={`hover:bg-gray-50 transition-colors ${!r.is_active ? "opacity-50" : ""}`}>
                  <td className="px-4 py-3 font-medium text-gray-900">{r.name}</td>
                  <td className="px-4 py-3 text-gray-600">{RULE_TYPE_LABELS[r.rule_type] ?? r.rule_type}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">
                    {r.client_type_trigger && <span>Cliente: <b>{r.client_type_trigger}</b></span>}
                    {r.min_quantity && <span>Min. qty: <b>{r.min_quantity}</b></span>}
                    {!r.client_type_trigger && !r.min_quantity && "—"}
                  </td>
                  <td className="px-4 py-3 text-right font-semibold text-brand-700">
                    {r.discount_type === "percentage" ? `${r.discount_value}%` : `Bs. ${r.discount_value}`}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-500">{r.priority}</td>
                  <td className="px-4 py-3 text-center">
                    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${r.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                      {r.is_active ? "Activa" : "Inactiva"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => handleToggle(r)}
                        className={`p-1.5 rounded transition-colors ${r.is_active ? "text-gray-400 hover:text-amber-500" : "text-gray-400 hover:text-green-600"}`}
                        title={r.is_active ? "Desactivar" : "Activar"}
                      >
                        <Power size={14} />
                      </button>
                      <button
                        onClick={() => handleDelete(r)}
                        className="p-1.5 text-gray-400 hover:text-red-500 transition-colors rounded"
                        title="Eliminar"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Nueva regla de precio" width="max-w-md">
        <form onSubmit={handleCreate} className="space-y-4">
          <FormField
            label="Nombre *"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="Descuento mayorista 15%"
          />

          <div className="grid grid-cols-2 gap-4">
            <SelectField
              label="Tipo de regla"
              value={form.rule_type}
              onChange={(e) => setForm({ ...form, rule_type: e.target.value })}
            >
              <option value="client_type">Tipo de cliente</option>
              <option value="quantity_threshold">Cantidad mínima</option>
              <option value="category_discount">Categoría</option>
            </SelectField>

            <SelectField
              label="Tipo de descuento"
              value={form.discount_type}
              onChange={(e) => setForm({ ...form, discount_type: e.target.value })}
            >
              <option value="percentage">Porcentaje (%)</option>
              <option value="fixed_amount">Monto fijo ($)</option>
            </SelectField>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <FormField
              label={`Valor del descuento ${form.discount_type === "percentage" ? "(%)" : "(Bs.)"}`}
              type="number"
              step="0.01"
              value={form.discount_value}
              onChange={(e) => setForm({ ...form, discount_value: parseFloat(e.target.value) || 0 })}
            />
            <FormField
              label="Prioridad"
              type="number"
              value={form.priority}
              onChange={(e) => setForm({ ...form, priority: parseInt(e.target.value) || 0 })}
            />
          </div>

          {form.rule_type === "client_type" && (
            <SelectField
              label="Aplica a tipo de cliente"
              value={form.client_type_trigger ?? ""}
              onChange={(e) => setForm({ ...form, client_type_trigger: e.target.value || undefined })}
            >
              <option value="">Todos los clientes</option>
              <option value="retail">Retail</option>
              <option value="wholesale">Mayorista</option>
            </SelectField>
          )}

          {form.rule_type === "quantity_threshold" && (
            <FormField
              label="Cantidad mínima"
              type="number"
              step="0.001"
              value={form.min_quantity ?? ""}
              onChange={(e) => setForm({ ...form, min_quantity: parseFloat(e.target.value) || undefined })}
            />
          )}

          <div className="grid grid-cols-2 gap-4">
            <FormField
              label="Válida desde"
              type="datetime-local"
              value={form.valid_from ?? ""}
              onChange={(e) => setForm({ ...form, valid_from: e.target.value || undefined })}
            />
            <FormField
              label="Válida hasta"
              type="datetime-local"
              value={form.valid_until ?? ""}
              onChange={(e) => setForm({ ...form, valid_until: e.target.value || undefined })}
            />
          </div>

          {formError && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {formError}
            </p>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="secondary" onClick={() => setModalOpen(false)}>
              Cancelar
            </Button>
            <Button type="submit" loading={saving}>
              Crear regla
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
