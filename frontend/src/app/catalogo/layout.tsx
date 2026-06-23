import type { Metadata } from "next";

export const metadata: Metadata = {
  title: {
    template: "%s | Black Horse Talabartería",
    default: "Catálogo | Black Horse Talabartería",
  },
  description:
    "Artículos de cuero artesanales: monturas, riendas, accesorios equinos y bovinos. Fabricación propia en Bolivia.",
};

const WA_PHONE = process.env.NEXT_PUBLIC_WHATSAPP_PHONE ?? "591XXXXXXXXX";

export default function CatalogoLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen flex flex-col bg-brand-50">
      {/* Header público */}
      <header className="bg-brand-800 text-white shadow-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
          <a href="/catalogo" className="flex items-center gap-3">
            <div className="w-10 h-10 bg-brand-500 rounded-full flex items-center justify-center text-white font-bold text-lg">
              BH
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight">Black Horse</h1>
              <p className="text-brand-200 text-xs">Talabartería artesanal</p>
            </div>
          </a>
          <div className="text-right hidden sm:block">
            <p className="text-brand-200 text-sm">Contacto</p>
            <a
              href={`https://wa.me/${WA_PHONE}`}
              className="text-green-400 font-semibold text-sm hover:text-green-300 transition-colors"
              target="_blank"
              rel="noopener noreferrer"
            >
              WhatsApp
            </a>
          </div>
        </div>
        <nav className="bg-brand-700 border-t border-brand-600">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex gap-6 py-2 overflow-x-auto text-sm">
              <a
                href="/catalogo"
                className="text-brand-100 hover:text-white whitespace-nowrap transition-colors"
              >
                Todo el catálogo
              </a>
            </div>
          </div>
        </nav>
      </header>

      {/* Contenido principal */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>

      {/* Footer */}
      <footer className="bg-brand-900 text-brand-300 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-8">
            <div>
              <h3 className="text-white font-semibold mb-2">Black Horse Talabartería</h3>
              <p className="text-sm">Artículos de cuero artesanales desde 1985.</p>
            </div>
            <div>
              <h3 className="text-white font-semibold mb-2">Dirección</h3>
              <p className="text-sm">Av. Principal 123, Santa Cruz, Bolivia</p>
            </div>
            <div>
              <h3 className="text-white font-semibold mb-2">Contacto</h3>
              <a
                href={`https://wa.me/${WA_PHONE}`}
                className="text-green-400 hover:text-green-300 text-sm block"
                target="_blank"
                rel="noopener noreferrer"
              >
                WhatsApp
              </a>
            </div>
          </div>
          <p className="text-center text-brand-500 text-xs mt-8">
            © {new Date().getFullYear()} Black Horse Talabartería. Todos los derechos reservados.
          </p>
        </div>
      </footer>
    </div>
  );
}
