import { useEffect, useState } from "react";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { GlassCard } from "../components/common/GlassCard";
import { api } from "../services/api";
import type { ReportMeta } from "../types/analysis";

export function Reports() {
  const [rows, setRows] = useState<ReportMeta[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .reports()
      .then(setRows)
      .catch((err: Error) => setError(err.message));
  }, []);

  return (
    <div className="space-y-4">
      <h1 className="font-display text-3xl">Generated reports</h1>
      <p className="text-sm text-slate-400">
        Reports are created from a stored analysis. Use Download Report on the results page or
        regenerate from history.
      </p>
      <ErrorBanner message={error} />
      <GlassCard>
        <div className="space-y-3">
          {rows.map((row) => (
            <div key={row.id} className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-white/5 px-4 py-3">
              <div>
                <p className="font-medium">@{row.username}</p>
                <p className="text-xs text-slate-500">
                  {row.format.toUpperCase()} · analysis #{row.analysis_id} · {new Date(row.created_at).toLocaleString()}
                </p>
              </div>
              <a href={api.reportDownloadUrl(row.id)} className="text-sm text-accent">
                Download
              </a>
            </div>
          ))}
          {rows.length === 0 && <p className="text-sm text-slate-500">No reports generated yet.</p>}
        </div>
      </GlassCard>
    </div>
  );
}
