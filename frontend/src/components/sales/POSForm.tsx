"use client";

import { useEffect, useState } from "react";
import { Plus, Minus, Trash2, ShoppingCart, Search } from "lucide-react";
import { productsService } from "@/services/products.service";
import { clientsService } from "@/services/clients.service";
import { salesService } from "@/services/sales.service";
import { formatCurrency } from "@/lib/formatters";
import { SelectField } from "@/components/ui/FormField";
import { Button } from "@/components/ui/Button";
import type { Client, PaymentType, Product, Sale } from "@/types";

interface CartItem {
  product: Product;
  quantity: number;
}

interface POSFormProps {
  onSuccess: (sale: Sale) => void;
  onCancel: () => void;
}

const PAYMENT_LABELS: Record<PaymentType, string> = {
  cash: "Efectivo",
  transfer: "Transferencia",
  card: "Tarjeta",
  mixed: "Combinado",
};

export function POSForm({ onSuccess, onCancel }: POSFormProps) {
  const [products, setProducts] = useState<Product[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [cart, setCart] = useState<CartItem[]>([]);
  const [productSearch, setProductSearch] = useState("");
  const [clientId, setClientId] = useState<string>("");
  const [paymentType, setPaymentType] = useState<PaymentType>("cash");
  const [saleType, setSaleType] = useState<"retail" | "wholesale">("retail");
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    productsService.list({ active_only: true, limit: 200 }).then((r) => setProducts(r.items));
    clientsService.list({ active_only: true, limit: 200 }).then((r) => setClients(r.items));
  }, []);

  // Sincronizar tipo de venta con tipo de cliente seleccionado
  useEffect(() => {
    if (!clientId) return;
    const client = clients.find((c) => c.id === clientId);
    if (client?.client_type === "wholesale") setSaleType("wholesale");
    else setSaleType("retail");
  }, [clientId, clients]);

  const filteredProducts = products.filter(
    (p) =>
      (p.name.toLowerCase().includes(productSearch.toLowerCase()) ||
        p.sku.toLowerCase().includes(productSearch.toLowerCase())) &&
      !cart.some((i) => i.product.id === p.id)
  );

  const addToCart = (product: Product) => {
    setCart((prev) => [...prev, { product, quantity: 1 }]);
    setProductSearch("");
  };

  const updateQty = (productId: string, delta: number) => {
    setCart((prev) =>
      prev
        .map((item) =>
          item.product.id === productId
            ? { ...item, quantity: Math.max(0, item.quantity + delta) }
            : item
        )
        .filter((item) => item.quantity > 0)
    );
  };

  const removeFromCart = (productId: string) => {
    setCart((prev) => prev.filter((i) => i.product.id !== productId));
  };

  const getUnitPrice = (p: Product) =>
    Number(saleType === "wholesale" && p.wholesale_price != null ? p.wholesale_price : p.base_price);

  const subtotal = cart.reduce((acc, i) => acc + getUnitPrice(i.product) * i.quantity, 0);

  const handleSubmit = async () => {
    if (cart.length === 0) return;
    setError(null);
    setLoading(true);
    try {
      const sale = await salesService.create({
        items: cart.map((i) => ({ product_id: i.product.id, quantity: i.quantity })),
        payment_type: paymentType,
        sale_type: saleType,
        client_id: clientId || undefined,
        notes: notes || undefined,
      });
      onSuccess(sale);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error al procesar la venta");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid grid-cols-2 gap-6">
      {/* — Selector de productos — */}
      <div className="space-y-4">
        <h3 className="font-semibold text-gray-800 text-sm">Agregar productos</h3>

        <div className="relative">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Buscar producto…"
            value={productSearch}
            onChange={(e) => setProductSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-400"
          />
        </div>

        {productSearch.length > 0 && (
          <div className="border border-gray-200 rounded-lg overflow-hidden max-h-52 overflow-y-auto">
            {filteredProducts.length === 0 ? (
              <p className="px-4 py-3 text-sm text-gray-400">Sin resultados</p>
            ) : (
              filteredProducts.slice(0, 10).map((p) => (
                <button
                  key={p.id}
                  onClick={() => addToCart(p)}
                  className="w-full flex items-center justify-between px-4 py-2.5 text-sm hover:bg-brand-50 transition-colors text-left"
                >
                  <div>
                    <div className="font-medium text-gray-900">{p.name}</div>
                    <div className="text-xs text-gray-400 font-mono">{p.sku}</div>
                  </div>
                  <div className="text-right text-gray-600 text-xs">
                    <div>{formatCurrency(getUnitPrice(p))}</div>
                    {p.quantity_on_hand !== null && (
                      <div className={p.quantity_on_hand <= 0 ? "text-red-500" : "text-gray-400"}>
                        stock: {p.quantity_on_hand}
                      </div>
                    )}
                  </div>
                </button>
              ))
            )}
          </div>
        )}

        {/* Opciones de venta */}
        <div className="space-y-3 pt-2 border-t border-gray-100">
          <div className="grid grid-cols-2 gap-3">
            <SelectField label="Tipo de venta" value={saleType} onChange={(e) => setSaleType(e.target.value as "retail" | "wholesale")}>
              <option value="retail">Retail</option>
              <option value="wholesale">Mayorista</option>
            </SelectField>
            <SelectField label="Forma de pago" value={paymentType} onChange={(e) => setPaymentType(e.target.value as PaymentType)}>
              {(Object.entries(PAYMENT_LABELS) as [PaymentType, string][]).map(([v, l]) => (
                <option key={v} value={v}>{l}</option>
              ))}
            </SelectField>
          </div>

          <SelectField label="Cliente (opcional)" value={clientId} onChange={(e) => setClientId(e.target.value)}>
            <option value="">Sin cliente asociado</option>
            {clients.map((c) => (
              <option key={c.id} value={c.id}>
                {c.full_name} — {c.phone}
              </option>
            ))}
          </SelectField>

          <div className="space-y-1">
            <label className="block text-sm font-medium text-gray-700">Notas</label>
            <textarea
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Observaciones de la venta…"
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-400 resize-none"
            />
          </div>
        </div>
      </div>

      {/* — Carrito — */}
      <div className="flex flex-col">
        <h3 className="font-semibold text-gray-800 text-sm mb-4">
          Carrito{" "}
          {cart.length > 0 && (
            <span className="text-gray-400 font-normal">({cart.length} ítem{cart.length !== 1 ? "s" : ""})</span>
          )}
        </h3>

        <div className="flex-1 space-y-2 min-h-[180px]">
          {cart.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-32 text-gray-300">
              <ShoppingCart size={28} className="mb-2" />
              <span className="text-sm">Carrito vacío</span>
            </div>
          ) : (
            cart.map(({ product, quantity }) => (
              <div key={product.id} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-gray-900 truncate">{product.name}</div>
                  <div className="text-xs text-gray-500">
                    {formatCurrency(getUnitPrice(product))} × {quantity} ={" "}
                    <span className="font-medium text-gray-700">
                      {formatCurrency(getUnitPrice(product) * quantity)}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <button
                    onClick={() => updateQty(product.id, -1)}
                    className="w-6 h-6 flex items-center justify-center rounded border border-gray-200 hover:bg-gray-100 transition-colors"
                  >
                    <Minus size={11} />
                  </button>
                  <span className="w-8 text-center text-sm font-medium">{quantity}</span>
                  <button
                    onClick={() => updateQty(product.id, 1)}
                    className="w-6 h-6 flex items-center justify-center rounded border border-gray-200 hover:bg-gray-100 transition-colors"
                  >
                    <Plus size={11} />
                  </button>
                  <button
                    onClick={() => removeFromCart(product.id)}
                    className="ml-1 text-gray-300 hover:text-red-500 transition-colors"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Totales */}
        <div className="border-t border-gray-200 pt-4 mt-4 space-y-1.5">
          <div className="flex justify-between text-sm text-gray-600">
            <span>Subtotal</span>
            <span>{formatCurrency(subtotal)}</span>
          </div>
          <div className="flex justify-between text-sm text-gray-400 italic">
            <span>Descuentos</span>
            <span>calculados al confirmar</span>
          </div>
          <div className="flex justify-between text-base font-bold text-gray-900 pt-1 border-t border-gray-100">
            <span>Total estimado</span>
            <span>{formatCurrency(subtotal)}</span>
          </div>
        </div>

        {error && (
          <p className="mt-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
            {error}
          </p>
        )}

        <div className="flex gap-2 mt-4">
          <Button type="button" variant="secondary" className="flex-1" onClick={onCancel}>
            Cancelar
          </Button>
          <Button
            className="flex-1"
            disabled={cart.length === 0}
            loading={loading}
            onClick={handleSubmit}
          >
            Confirmar venta
          </Button>
        </div>
      </div>
    </div>
  );
}
