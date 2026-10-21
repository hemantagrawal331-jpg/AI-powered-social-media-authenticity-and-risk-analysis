export function ScoreBar({ label, value }: { label: string; value: number }) {
  const width = Math.max(0, Math.min(100, value));
  return (
    <div className="space-y-1.5">
      <div className="flex items-baseline justify-between gap-3 text-sm">
        <span>{label}</span>
        <span className="font-mono text-xs text-muted">{Math.round(value)}</span>
      </div>
      <div className="h-px bg-line">
        <div className="h-0.5 bg-ink transition-[width] duration-700" style={{ width: `${width}%` }} />
      </div>
    </div>
  );
}
