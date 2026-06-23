export default function ProductoLoading() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 animate-pulse">
      <div className="aspect-square rounded-2xl bg-brand-100" />
      <div className="space-y-4">
        <div className="h-4 bg-brand-100 rounded w-1/3" />
        <div className="h-8 bg-brand-100 rounded w-2/3" />
        <div className="h-24 bg-brand-100 rounded" />
        <div className="h-12 bg-brand-100 rounded w-1/2" />
      </div>
    </div>
  );
}
