import type { AnalysisResult } from "../../types/analysis";

export function EvidenceWaterfall({ result }: { result: AnalysisResult }) {
  const rows = result.evidence_waterfall || [];
  if (!rows.length) return <p className="text-sm text-muted">No evidence steps were returned for this analysis.</p>;
  return (
    <div className="space-y-2">
      {rows.map((row) => {
        const lowersRisk = row.delta < 0;
        const prior = row.kind === "prior" || row.kind === "final";
        return (
          <div key={`${row.label}-${row.value}`} className="grid grid-cols-[1fr_auto_auto] items-baseline gap-3 border-b border-line py-2 text-sm last:border-b-0">
            <p>{row.label}</p>
            <p className={`font-mono text-xs ${prior ? "text-muted" : lowersRisk ? "text-verified" : row.delta > 0 ? "text-signal" : "text-muted"}`}>
              {prior ? "—" : `${row.delta > 0 ? "+" : ""}${row.delta}`}
            </p>
            <p className="w-14 text-right font-mono text-xs">{row.value}</p>
          </div>
        );
      })}
    </div>
  );
}
