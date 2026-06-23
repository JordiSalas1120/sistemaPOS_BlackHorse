export default function CatalogoLoading() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-6">
      {Array.from({ length: 6 }).map((_, i) => (
        <div
          key={i}
          className="bg-white rounded-2xl border border-brand-100 overflow-hidden animate-pulse"
        >
          <div className="aspect-square bg-brand-100" />
          <div className="p-4 space-y-2">
            <div className="h-4 bg-brand-100 rounded w-3/4" />
            <div className="h-3 bg-brand-100 rounded w-1/3" />
            <div className="h-8 bg-brand-100 rounded mt-3" />
          </div>
        </div>
      ))}
    </div>
  );
}
