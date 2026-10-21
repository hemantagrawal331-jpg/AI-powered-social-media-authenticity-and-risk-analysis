import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { GlassCard } from "../components/common/GlassCard";
import { RiskBadge } from "../components/common/RiskBadge";
import { api, persistResult } from "../services/api";
import type { HistoryItem } from "../types/analysis";

export function History() {
  const navigate = useNavigate();
  const [rows, setRows] = useState<HistoryItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<number[]>([]);

  const refresh = () => {
    api
      .history()
      .then(setRows)
      .catch((err: Error) => setError(err.message));
  };

  useEffect(() => {
    refresh();
  }, []);

  const view = async (id: number) => {
    try {
      const result = await api.historyItem(id);
      persistResult(result);
      navigate(`/results/${id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not open result");
    }
  };

  const remove = async (id: number) => {
    try {
      await api.deleteHistory(id);
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  };

  const toggle = (id: number) => {
    setSelected((current) => (current.includes(id) ? current.filter((item) => item !== id) : [...current, id].slice(-2)));
  };

  const compareSelected = async () => {
    if (selected.length !== 2) {
      setError("Select exactly two analyses to compare.");
      return;
    }
    try {
      const [a, b] = await Promise.all(selected.map((id) => api.historyInput(id)));
      sessionStorage.setItem("fakeguard:compare-pair", JSON.stringify([a, b]));
      navigate("/compare");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Compare failed");
    }
  };

  const report = async (id: number) => {
    try {
      const created = await api.createReport(id, "pdf");
      window.open(api.reportDownloadUrl(created.id), "_blank");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Report failed");
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl">Analysis history</h1>
          <p className="mt-1 text-sm text-slate-400">Optional local store. Select two rows to inspect change between analyses.</p>
        </div>
        <button
          type="button"
          onClick={() => void compareSelected()}
          className="rounded-xl border border-white/10 px-4 py-2 text-sm"
        >
          Compare selected
        </button>
      </div>
      <ErrorBanner message={error} />
      <GlassCard>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-slate-400">
              <tr>
                <th className="pb-3" />
                <th>Username</th>
                <th>Platform</th>
                <th>Risk</th>
                <th>Purpose</th>
                <th>Date</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id} className="border-t border-white/5">
                  <td className="py-3">
                    <input type="checkbox" checked={selected.includes(row.id)} onChange={() => toggle(row.id)} />
                  </td>
                  <td>@{row.username}</td>
                  <td>{row.platform}</td>
                  <td>
                    <RiskBadge level={`${row.risk_level} (${Math.round(row.fake_probability)}%)`} />
                  </td>
                  <td>{row.purpose}</td>
                  <td className="font-mono text-xs">{new Date(row.created_at).toLocaleString()}</td>
                  <td className="space-x-2 text-right">
                    <button type="button" className="text-accent" onClick={() => void view(row.id)}>
                      View
                    </button>
                    <button type="button" className="text-slate-300" onClick={() => void report(row.id)}>
                      Report
                    </button>
                    <button type="button" className="text-rose-300" onClick={() => void remove(row.id)}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-6 text-slate-500">
                    No analyses stored yet. History is optional and local.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </GlassCard>
    </div>
  );
}
