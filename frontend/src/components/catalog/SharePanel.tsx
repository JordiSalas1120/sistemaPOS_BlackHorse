"use client";

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface SharePanelProps {
  /** Ruta pública a compartir, ej: "/catalogo" o "/catalogo/EQU-00001". */
  path: string;
  /** Texto del botón disparador. */
  label?: string;
  /** Mensaje sugerido para WhatsApp. */
  message?: string;
}

export function SharePanel({ path, label = "Compartir", message }: SharePanelProps) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [shareUrl, setShareUrl] = useState(path);

  useEffect(() => {
    if (typeof window !== "undefined") {
      setShareUrl(`${window.location.origin}${path}`);
    }
  }, [path]);

  const qr = `${API}/api/v1/catalog/qr?path=${encodeURIComponent(path)}`;
  const waText = encodeURIComponent(`${message ? message + " " : ""}${shareUrl}`);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      /* clipboard no disponible */
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-2 rounded-full border border-brand-300 bg-white px-4 py-2 text-sm font-medium text-brand-700 hover:bg-brand-50 transition-colors"
      >
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
          <circle cx="18" cy="5" r="3" /><circle cx="6" cy="12" r="3" /><circle cx="18" cy="19" r="3" />
          <path d="M8.6 13.5l6.8 4M15.4 6.5l-6.8 4" />
        </svg>
        {label}
      </button>

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
          onClick={() => setOpen(false)}
        >
          <div
            className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6 text-center"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-brand-900">Compartir catálogo</h3>
              <button onClick={() => setOpen(false)} className="text-brand-400 hover:text-brand-700 text-xl leading-none">
                ×
              </button>
            </div>

            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={qr}
              alt="Código QR del catálogo"
              className="mx-auto w-44 h-44 rounded-xl border border-brand-100 p-2"
            />
            <p className="text-xs text-brand-400 mt-2">Escaneá para abrir en el celular</p>

            <div className="mt-4 flex items-center gap-2 rounded-lg border border-brand-200 bg-brand-50 px-3 py-2">
              <span className="truncate text-sm text-brand-700 flex-1 text-left">{shareUrl}</span>
              <button
                onClick={copy}
                className="text-xs font-medium text-brand-700 hover:text-brand-900 whitespace-nowrap"
              >
                {copied ? "¡Copiado!" : "Copiar"}
              </button>
            </div>

            <a
              href={`https://wa.me/?text=${waText}`}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-3 flex items-center justify-center gap-2 rounded-lg bg-green-500 hover:bg-green-600 text-white font-medium py-2.5 transition-colors"
            >
              Compartir por WhatsApp
            </a>
          </div>
        </div>
      )}
    </>
  );
}
