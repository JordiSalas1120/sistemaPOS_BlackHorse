"use client";

import { useEffect, useState } from "react";
import { Users, Plus, Search, Pencil, X } from "lucide-react";
import { clientsService } from "@/services/clients.service";
import { formatDate } from "@/lib/formatters";
import { Modal } from "@/components/ui/Modal";
import { ClientForm } from "@/components/clients/ClientForm";
import { Button } from "@/components/ui/Button";
import type { Client, ClientType } from "@/types";

const TYPE_LABELS: Record<ClientType, string> = { retail: "Retail", wholesale: "Mayorista" };

export default function ClientesPage() {
  const [clients, setClients] = useState<Client[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Client | null>(null);
  const [addingTag, setAddingTag] = useState<string | null>(null); // client id
  const [tagInput, setTagInput] = useState("");

  const load = () => {
    setLoading(true);
    clientsService
      .list({ active_only: false, limit: 200 })
      .then((res) => { setClients(res.items); setTotal(res.total); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const filtered = clients.filter(
    (c) =>
      c.full_name.toLowerCase().includes(search.toLowerCase()) ||
      c.phone.includes(search) ||
      (c.email ?? "").toLowerCase().includes(search.toLowerCase())
  );

  const handleSuccess = () => {
    setModalOpen(false);
    setEditing(null);
    load();
  };

  const handleRemoveTag = async (client: Client, tag: string) => {
    await clientsService.removeTag(client.id, tag);
    load();
  };

  const handleAddTag = async (clientId: string) => {
    const tag = tagInput.trim();
    if (!tag) return;
    await clientsService.addTag(clientId, tag);
    setAddingTag(null);
    setTagInput("");
    load();
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Clientes</h1>
          <p className="text-sm text-gray-500 mt-0.5">{total} clientes registrados</p>
        </div>
        <Button onClick={() => { setEditing(null); setModalOpen(true); }}>
          <Plus size={16} className="mr-1.5" />
          Nuevo cliente
        </Button>
      </div>

      <div className="relative mb-4 max-w-sm">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          placeholder="Buscar por nombre, teléfono o email…"
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
                <th className="text-left px-4 py-3 font-medium text-gray-600">Nombre</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Teléfono</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Tipo</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Tags CRM</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Última compra</th>
                <th className="text-center px-4 py-3 font-medium text-gray-600">Estado</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-gray-400">
                    <Users size={24} className="mx-auto mb-2 opacity-40" />
                    Sin clientes
                  </td>
                </tr>
              )}
              {filtered.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50 transition-colors align-top">
                  <td className="px-4 py-3 font-medium text-gray-900">
                    {c.full_name}
                    {c.email && <div className="text-xs text-gray-400 font-normal">{c.email}</div>}
                  </td>
                  <td className="px-4 py-3 text-gray-600">{c.phone}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${c.client_type === "wholesale" ? "bg-purple-100 text-purple-700" : "bg-gray-100 text-gray-600"}`}>
                      {TYPE_LABELS[c.client_type]}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1 items-center">
                      {c.tags.map((tag) => (
                        <span key={tag} className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-brand-100 text-brand-700 rounded text-xs group">
                          {tag}
                          <button
                            onClick={() => handleRemoveTag(c, tag)}
                            className="opacity-0 group-hover:opacity-100 transition-opacity"
                            title="Quitar tag"
                          >
                            <X size={10} />
                          </button>
                        </span>
                      ))}
                      {addingTag === c.id ? (
                        <form
                          onSubmit={(e) => { e.preventDefault(); handleAddTag(c.id); }}
                          className="flex items-center gap-1"
                        >
                          <input
                            autoFocus
                            value={tagInput}
                            onChange={(e) => setTagInput(e.target.value)}
                            onBlur={() => { setAddingTag(null); setTagInput(""); }}
                            placeholder="nuevo tag"
                            className="px-1.5 py-0.5 text-xs border border-brand-300 rounded focus:outline-none focus:ring-1 focus:ring-brand-400 w-24"
                          />
                        </form>
                      ) : (
                        <button
                          onClick={() => { setAddingTag(c.id); setTagInput(""); }}
                          className="px-1.5 py-0.5 text-xs text-gray-400 hover:text-brand-600 border border-dashed border-gray-300 hover:border-brand-400 rounded transition-colors"
                          title="Agregar tag"
                        >
                          + tag
                        </button>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">
                    {c.last_purchase_at ? formatDate(c.last_purchase_at) : "—"}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${c.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                      {c.is_active ? "Activo" : "Inactivo"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => { setEditing(c); setModalOpen(true); }}
                      className="p-1.5 text-gray-400 hover:text-brand-600 transition-colors rounded"
                      title="Editar"
                    >
                      <Pencil size={14} />
                    </button>
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
        title={editing ? "Editar cliente" : "Nuevo cliente"}
      >
        <ClientForm
          client={editing ?? undefined}
          onSuccess={handleSuccess}
          onCancel={() => { setModalOpen(false); setEditing(null); }}
        />
      </Modal>
    </div>
  );
}
