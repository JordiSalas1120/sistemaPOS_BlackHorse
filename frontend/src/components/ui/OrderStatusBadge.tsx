import type { ProductionOrderStatus } from "@/types/production";

const STATUS_CONFIG: Record<
  ProductionOrderStatus,
  { label: string; className: string }
> = {
  draft: {
    label: "Borrador",
    className: "bg-gray-100 text-gray-700 border border-gray-300",
  },
  in_progress: {
    label: "En progreso",
    className: "bg-yellow-100 text-yellow-800 border border-yellow-300",
  },
  completed: {
    label: "Completada",
    className: "bg-green-100 text-green-800 border border-green-300",
  },
  cancelled: {
    label: "Cancelada",
    className: "bg-red-100 text-red-700 border border-red-300",
  },
};

interface OrderStatusBadgeProps {
  status: ProductionOrderStatus;
}

export function OrderStatusBadge({ status }: OrderStatusBadgeProps) {
  const config = STATUS_CONFIG[status];
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.className}`}
    >
      {config.label}
    </span>
  );
}
