import Link from "next/link";

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 p-8">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-brand-600">Black Horse - System</h1>
        <p className="mt-2 text-gray-500">Sistema de gestión de tienda y clientes</p>
      </div>
      <Link
        href="/dashboard"
        className="rounded-lg bg-brand-500 px-6 py-3 text-white font-medium hover:bg-brand-600 transition-colors"
      >
        Ir al Dashboard
      </Link>
    </main>
  );
}
