"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Copy, Check, Download, ExternalLink, BookOpen } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const QR_URL = `${API}/api/v1/catalog/qr?path=/catalogo`;

export function CatalogShareCard() {
  const [catalogUrl, setCatalogUrl] = useState("/catalogo");
  const [revistaUrl, setRevistaUrl] = useState("/revista");
  const [copied, setCopied] = useState(false);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined") {
      setCatalogUrl(`${window.location.origin}/catalogo`);
      setRevistaUrl(`${window.location.origin}/revista`);
    }
  }, []);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(catalogUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      /* clipboard no disponible */
    }
  };

  const downloadQr = async () => {
    setDownloading(true);
    try {
      const res = await fetch(QR_URL);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "catalogo-blackhorse-qr.png";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {
      window.open(QR_URL, "_blank");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 max-w-2xl">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="font-semibold text-gray-900">Catálogo público</h3>
          <p className="text-xs text-gray-500">Compartí el catálogo por URL o código QR</p>
        </div>
        <span className="text-xs font-medium text-green-700 bg-green-100 px-2 py-1 rounded-full">
          En línea
        </span>
      </div>

      <div className="flex flex-col sm:flex-row gap-5">
        {/* QR */}
        <div className="flex flex-col items-center gap-2 shrink-0">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={QR_URL}
            alt="Código QR del catálogo"
            className="w-36 h-36 rounded-lg border border-gray-200 p-2"
          />
          <button
            onClick={downloadQr}
            disabled={downloading}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-brand-700 hover:text-brand-900 disabled:opacity-60"
          >
            <Download size={14} />
            {downloading ? "Descargando…" : "Descargar QR"}
          </button>
        </div>

        {/* URL + acciones */}
        <div className="flex-1 min-w-0 flex flex-col gap-3">
          <div>
            <label className="text-xs font-medium text-gray-500">Enlace del catálogo</label>
            <div className="mt-1 flex items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2">
              <span className="truncate text-sm text-gray-700 flex-1">{catalogUrl}</span>
              <button
                onClick={copy}
                className="inline-flex items-center gap-1 text-xs font-medium text-brand-700 hover:text-brand-900 whitespace-nowrap"
              >
                {copied ? <Check size={14} /> : <Copy size={14} />}
                {copied ? "Copiado" : "Copiar"}
              </button>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <Link
              href="/catalogo"
              target="_blank"
              className="inline-flex items-center gap-1.5 rounded-lg bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium px-4 py-2 transition-colors"
            >
              <ExternalLink size={15} /> Abrir catálogo
            </Link>
            <Link
              href="/revista"
              target="_blank"
              className="inline-flex items-center gap-1.5 rounded-lg border border-brand-300 text-brand-700 hover:bg-brand-50 text-sm font-medium px-4 py-2 transition-colors"
            >
              <BookOpen size={15} /> Ver revista
            </Link>
            <a
              href={`https://wa.me/?text=${encodeURIComponent(`Mirá el catálogo de Black Horse Talabartería: ${catalogUrl}`)}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 rounded-lg bg-green-500 hover:bg-green-600 text-white text-sm font-medium px-4 py-2 transition-colors"
            >
              WhatsApp
            </a>
          </div>

          <p className="text-xs text-gray-400">
            Para compartir fuera de esta computadora, configurá la IP/dominio del servidor
            en las variables del catálogo.
          </p>
        </div>
      </div>
    </div>
  );
}
