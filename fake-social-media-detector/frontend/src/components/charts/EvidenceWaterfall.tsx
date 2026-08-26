import type { AnalysisResult } from "../../types/analysis";

export function EvidenceWaterfall({ result }: { result: AnalysisResult }) {
  const rows = result.evidence_waterfall || [];
  if (!rows.length) return null;
  return (
    <div className="space-y-2">
      {rows.map((row) => {
        const positive = row.delta < 0;
        const prior = row.kind === "prior" || row.kind === "final";
        return (
          <div key={`${row.label}-${row.value}`} className="grid grid-cols-[1fr_auto_auto] items-center gap-3 text-sm">
            <p className={prior ? "text-slate-200" : "text-slate-400"}>{row.label}</p>
            <p
              className={`font-mono text-xs ${
                prior ? "text-slate-500" : positive ? "text-emerald-300" : row.delta > 0 ? "text-rose-300" : "text-slate-500"
              }`}
            >
              {prior ? "—" : `${row.delta > 0 ? "+" : ""}${row.delta}%`}
            </p>
            <p className="w-14 text-right font-mono">{row.value}%</p>
          </div>
        );
      })}
    </div>
  );
}
