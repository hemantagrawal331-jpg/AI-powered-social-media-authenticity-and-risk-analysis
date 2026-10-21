import { BrainCircuit } from "lucide-react";
import { useEffect, useState } from "react";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { GlassCard } from "../components/common/GlassCard";
import { api } from "../services/api";

export function ModelLab() {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [feedback, setFeedback] = useState<{ counts: Record<string, number>; items: Record<string, unknown>[] } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [url, setUrl] = useState("https://instagram.com/crypto_giveaway_9283");
  const [ingest, setIngest] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    api.modelStatus().then(setData).catch((err: Error) => setError(err.message));
    api.modelFeedbackList().then(setFeedback).catch(() => undefined);
  }, []);

  const importances = ((data?.feature_importances as { feature: string; importance: number }[]) || []).map((item) => ({
    name: item.feature.replace(/_/g, " "),
    value: item.importance,
  }));
  const matrix = (data?.confusion_matrix as { tn: number; fp: number; fn: number; tp: number } | undefined) || {
    tn: 0,
    fp: 0,
    fn: 0,
    tp: 0,
  };

  return (
    <div className="space-y-6">
      <div>
        <p className="kicker flex items-center gap-2">
          <BrainCircuit className="h-3.5 w-3.5" /> Model lab
        </p>
        <h1 className="mt-2 font-display text-4xl tracking-tight">What the model was measured on</h1>
        <p className="mt-2 max-w-3xl text-sm text-muted">
          Holdout metrics are from overlapping synthetic archetypes (not live Instagram). Sophisticated
          bots were held out of training — that adversarial AUC is expected to be weak. Public page
          fetch runs from Analyzer when TinyFish is configured. It does not log in.
        </p>
      </div>
      <ErrorBanner message={error} />
      <div className="grid gap-4 md:grid-cols-4">
        <Stat label="Holdout accuracy" value={pct(data?.accuracy)} />
        <Stat label="F1" value={pct(data?.f1)} />
        <Stat label="PR-AUC" value={pct(data?.pr_auc)} />
        <Stat label="ROC-AUC" value={pct(data?.roc_auc)} />
        <Stat label="Brier (lower better)" value={num(data?.brier)} />
        <Stat label="ECE (lower better)" value={num(data?.ece)} />
        <Stat label="Adv. metadata AUC" value={pct(data?.adversarial_metadata_auc)} />
        <Stat label="Adv. content AUC" value={pct(data?.adversarial_content_only_auc)} />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <GlassCard title="Confusion matrix (test set)" className="lg:col-span-2">
          <p className="text-sm text-muted">
            Trained on {String(data?.training_rows ?? "—")} rows · tested on {String(data?.test_rows ?? "—")}
          </p>
          <div className="mt-4 grid max-w-3xl grid-cols-2 gap-3 text-center">
            <Cell title="True genuine" value={matrix.tn} />
            <Cell title="False alarm" value={matrix.fp} />
            <Cell title="Missed fake" value={matrix.fn} />
            <Cell title="True fake" value={matrix.tp} />
          </div>
        </GlassCard>
        <GlassCard title="What the forest uses most" className="lg:col-span-2">
          <ImportanceList rows={importances} />
        </GlassCard>
      </div>
      <GlassCard title="Platform APIs">
        <p className="text-sm leading-6 text-ink-soft">
          Paste an Instagram/X URL. FakeGuard will parse the username. It will not scrape the live
          profile.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <input value={url} onChange={(e) => setUrl(e.target.value)} className="input max-w-xl" />
          <button
            type="button"
            className="btn"
            onClick={() => void api.ingestUrl(url).then(setIngest).catch((err: Error) => setError(err.message))}
          >
            Parse URL
          </button>
        </div>
        {ingest && <p className="mt-3 text-sm text-ink-soft">{String(ingest.detail || "")}</p>}
      </GlassCard>
      <GlassCard title="Continuous validation (analyst labels)">
        <p className="text-sm text-muted">
          After an analysis, mark it genuine or fake on the results page. Stored labels:{" "}
          {JSON.stringify(feedback?.counts || {})}
        </p>
        <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-muted">
          {((data?.notes as string[]) || []).map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      </GlassCard>
    </div>
  );
}

function pct(value: unknown) {
  if (typeof value !== "number") return "—";
  return `${Math.round(value * 1000) / 10}%`;
}

function num(value: unknown) {
  if (typeof value !== "number") return "—";
  return String(Math.round(value * 1000) / 1000);
}

function ImportanceList({ rows }: { rows: { name: string; value: number }[] }) {
  const max = Math.max(...rows.map((row) => row.value), 0.001);
  if (!rows.length) return <p className="text-sm text-muted">Importances appear after the model file loads.</p>;
  return (
    <ul className="space-y-2">
      {rows.map((row) => (
        <li key={row.name} className="grid items-center gap-3 sm:grid-cols-[minmax(12rem,18rem)_1fr_4rem]">
          <span className="text-sm">{row.name}</span>
          <span className="h-1 bg-line">
            <span className="block h-1 bg-ink" style={{ width: `${(row.value / max) * 100}%` }} />
          </span>
          <span className="font-mono text-xs text-muted">{row.value.toFixed(3)}</span>
        </li>
      ))}
    </ul>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-line bg-paper-raised p-4">
      <p className="text-xs uppercase tracking-[0.2em] text-muted">{label}</p>
      <p className="mt-2 font-display text-2xl">{value}</p>
    </div>
  );
}

function Cell({ title, value }: { title: string; value: number }) {
  return (
    <div className="border border-line bg-paper p-4">
      <p className="text-xs text-muted">{title}</p>
      <p className="mt-1 font-display text-2xl">{value}</p>
    </div>
  );
}
