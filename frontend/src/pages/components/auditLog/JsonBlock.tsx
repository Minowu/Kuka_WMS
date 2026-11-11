export default function JsonBlock({ title, value }: { title: string; value: unknown }) {
  if (value === null || value === undefined) return null;
  return (
    <div className="flex-1 min-w-[280px]">
      <div className="text-xs font-semibold text-slate-500 mb-1">{title}</div>
      <pre className="bg-slate-900 text-slate-100 text-xs rounded-lg p-3 max-h-72 overflow-auto text-left">
        {JSON.stringify(value, null, 2)}
      </pre>
    </div>
  );
}
