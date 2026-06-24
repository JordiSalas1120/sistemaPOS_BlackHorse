"use client";

export function PrintButton({
  label = "Descargar PDF",
  className,
}: {
  label?: string;
  className?: string;
}) {
  return (
    <button
      type="button"
      onClick={() => window.print()}
      className={
        className ??
        "inline-flex items-center gap-2 rounded-full border border-[#9a6b2f] bg-[#241208] px-6 py-3 text-sm font-medium tracking-wide text-[#f4d5a8] transition-colors hover:bg-[#3a2010]"
      }
    >
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
        <path d="M6 9V2h12v7M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2M6 14h12v8H6z" />
      </svg>
      {label}
    </button>
  );
}
