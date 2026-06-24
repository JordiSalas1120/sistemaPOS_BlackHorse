"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Package, Users, Warehouse, ShoppingCart, AlertTriangle, TrendingUp, Tag, Plus, Hammer } from "lucide-react";
import { productsService } from "@/services/products.service";
import { clientsService } from "@/services/clients.service";
import { inventoryService } from "@/services/inventory.service";
import { salesService } from "@/services/sales.service";
import { workshopService } from "@/services/workshop.service";
import { formatCurrency } from "@/lib/formatters";
import { Modal } from "@/components/ui/Modal";
import { POSForm } from "@/components/sales/POSForm";
import { Button } from "@/components/ui/Button";
import { CatalogShareCard } from "@/components/dashboard/CatalogShareCard";
import type { Sale } from "@/types";

interface KPIs {
  totalProducts: number;
  totalClients: number;
  lowStockCount: number;
  totalSales: number;
  todayRevenue: number;
}

export default function DashboardPage() {
  const [kpis, setKpis] = useState<KPIs | null>(null);
  const [posOpen, setPosOpen] = useState(false);
  const [inProgressCount, setInProgressCount] = useState(0);
  const [completedThisMonthCount, setCompletedThisMonthCount] = useState(0);

  const loadKpis = () => {
    const today = new Date().toDateString();
    Promise.all([
      productsService.list({ active_only: true, limit: 1 }),
      clientsService.list({ active_only: false, limit: 1 }),
      inventoryService.alerts(),
      salesService.list({ limit: 200 }),
    ]).then(([products, clients, alerts, sales]) => {
      const todaySales = sales.items.filter(
        (s) => s.status === "completed" && new Date(s.created_at).toDateString() === today
      );
      setKpis({
        totalProducts: products.total,
        totalClients: clients.total,
        lowStockCount: alerts.length,
        totalSales: sales.total,
        todayRevenue: todaySales.reduce((acc, s) => acc + Number(s.total), 0),
      });
    });

    Promise.all([
      workshopService.getInProgressCount(),
      workshopService.getCompletedThisMonthCount(),
    ])
      .then(([inProgress, completedMonth]) => {
        setInProgressCount(inProgress);
        setCompletedThisMonthCount(completedMonth);
      })
      .catch(() => {});
  };

  useEffect(loadKpis, []);

  const handlePOSSuccess = (_sale: Sale) => {
    setPosOpen(false);
    loadKpis();
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 mb-1">Panel de control</h1>
          <p className="text-gray-500 text-sm">Sistema de gestión para talabartería</p>
        </div>
        <Button onClick={() => setPosOpen(true)} className="gap-2">
          <Plus size={16} />
          Registrar venta
        </Button>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <KpiCard
          label="Ventas hoy"
          value={kpis ? formatCurrency(kpis.todayRevenue) : "—"}
          icon={TrendingUp}
          color="bg-green-100 text-green-700"
          href="/dashboard/ventas"
        />
        <KpiCard
          label="Total ventas"
          value={kpis ? `${kpis.totalSales}` : "—"}
          icon={ShoppingCart}
          color="bg-purple-100 text-purple-700"
          href="/dashboard/ventas"
        />
        <KpiCard
          label="Clientes"
          value={kpis ? `${kpis.totalClients}` : "—"}
          icon={Users}
          color="bg-blue-100 text-blue-700"
          href="/dashboard/clientes"
        />
        <KpiCard
          label="Productos activos"
          value={kpis ? `${kpis.totalProducts}` : "—"}
          icon={Package}
          color="bg-brand-100 text-brand-700"
          href="/dashboard/productos"
        />
      </div>

      {/* Producción */}
      <div className="max-w-2xl mb-6">
        <Link href="/dashboard/taller/ordenes">
          <div className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition-shadow cursor-pointer">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-medium text-gray-500 flex items-center gap-2">
                <Hammer size={15} className="text-brand-600" /> Producción
              </h3>
            </div>
            <div className="space-y-1">
              <p className="text-2xl font-bold text-brand-900">{inProgressCount}</p>
              <p className="text-xs text-gray-400">órdenes en curso</p>
              <p className="text-sm text-green-600 font-medium mt-2">
                {completedThisMonthCount} completadas este mes
              </p>
            </div>
          </div>
        </Link>
      </div>

      {/* Catálogo público: URL + QR + descarga */}
      <div className="mb-6">
        <CatalogShareCard />
      </div>

      {/* Accesos directos */}
      <div className="grid grid-cols-2 gap-4 max-w-2xl mb-6">
        {[
          { href: "/dashboard/productos",  label: "Productos",        description: "Catálogo y precios",        icon: Package,  color: "bg-brand-100 text-brand-700"  },
          { href: "/dashboard/inventario", label: "Inventario",       description: "Stock y movimientos",       icon: Warehouse, color: "bg-blue-100 text-blue-700"   },
          { href: "/dashboard/clientes",   label: "Clientes",         description: "CRM y segmentación",        icon: Users,    color: "bg-green-100 text-green-700"  },
          { href: "/dashboard/ventas",     label: "Ventas",           description: "Historial y exportación",   icon: ShoppingCart, color: "bg-purple-100 text-purple-700" },
          { href: "/dashboard/precios",    label: "Reglas de precio", description: "Descuentos y promociones",  icon: Tag,      color: "bg-amber-100 text-amber-700"  },
        ].map(({ href, label, description, icon: Icon, color }) => (
          <Link
            key={href}
            href={href}
            className="flex items-center gap-4 p-5 bg-white rounded-xl border border-gray-200 hover:border-brand-300 hover:shadow-sm transition-all"
          >
            <div className={`p-3 rounded-lg ${color}`}>
              <Icon size={20} />
            </div>
            <div>
              <div className="font-semibold text-gray-900">{label}</div>
              <div className="text-xs text-gray-500">{description}</div>
            </div>
          </Link>
        ))}
      </div>

      {/* Alertas */}
      {kpis && kpis.lowStockCount > 0 && (
        <div className="flex items-center gap-2 text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 max-w-2xl">
          <AlertTriangle size={16} />
          <span>
            <b>{kpis.lowStockCount}</b> producto{kpis.lowStockCount !== 1 ? "s" : ""} con stock bajo.{" "}
            <Link href="/dashboard/inventario" className="underline font-medium">Ver inventario</Link>
          </span>
        </div>
      )}

      {/* Modal POS */}
      <Modal open={posOpen} onClose={() => setPosOpen(false)} title="Registrar venta" width="max-w-4xl">
        <POSForm onSuccess={handlePOSSuccess} onCancel={() => setPosOpen(false)} />
      </Modal>
    </div>
  );
}

function KpiCard({
  label,
  value,
  icon: Icon,
  color,
  href,
}: {
  label: string;
  value: string;
  icon: React.ElementType;
  color: string;
  href: string;
}) {
  return (
    <Link
      href={href}
      className="bg-white rounded-xl border border-gray-200 p-5 hover:border-brand-300 hover:shadow-sm transition-all"
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</span>
        <div className={`p-2 rounded-lg ${color}`}>
          <Icon size={15} />
        </div>
      </div>
      <div className="text-2xl font-bold text-gray-900">{value}</div>
    </Link>
  );
}
