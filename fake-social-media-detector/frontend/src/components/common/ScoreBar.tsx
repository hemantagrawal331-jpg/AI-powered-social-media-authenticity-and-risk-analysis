export function ScoreBar({ label, value }: { label: string; value: number }) {
  const width = Math.max(0, Math.min(100, value));
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-sm">
        <span className="text-slate-300">{label}</span>
        <span className="font-mono text-slate-100">{Math.round(value)}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-white/5">
        <div
          className="risk-bar h-full rounded-full transition-all duration-700"
          style={{ width: `${width}%` }}
        />
      </div>
    </div>
  );
}
