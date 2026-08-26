import { BrainCircuit } from "lucide-react";
import { useEffect, useState } from "react";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
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
        <p className="flex items-center gap-2 text-xs uppercase tracking-[0.28em] text-accent">
          <BrainCircuit className="h-4 w-4" /> Model lab
        </p>
        <h1 className="mt-2 font-display text-3xl">Training data, validation, history, APIs</h1>
        <p className="mt-2 max-w-3xl text-sm text-slate-400">
          FakeGuard now trains a Random Forest on 4,000 labeled synthetic profiles, scores supplied
          timelines, and stores analyst labels. Live Instagram/X fetch is still off — those platforms
          require approved apps and do not allow scraping.
        </p>
      </div>
      <ErrorBanner message={error} />
      <div className="grid gap-4 md:grid-cols-4">
        <Stat label="Holdout accuracy" value={pct(data?.accuracy)} />
        <Stat label="Precision" value={pct(data?.precision)} />
        <Stat label="Recall" value={pct(data?.recall)} />
        <Stat label="ROC-AUC" value={pct(data?.roc_auc)} />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <GlassCard title="Confusion matrix (test set)">
          <p className="text-sm text-slate-400">
            Trained on {String(data?.training_rows ?? "—")} rows · tested on {String(data?.test_rows ?? "—")}
          </p>
          <div className="mt-4 grid grid-cols-2 gap-3 text-center">
            <Cell title="True genuine" value={matrix.tn} />
            <Cell title="False alarm" value={matrix.fp} />
            <Cell title="Missed fake" value={matrix.fn} />
            <Cell title="True fake" value={matrix.tp} />
          </div>
        </GlassCard>
        <GlassCard title="What the forest uses most">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={importances} layout="vertical">
              <XAxis type="number" tick={{ fill: "#94a3b8", fontSize: 11 }} />
              <YAxis type="category" dataKey="name" width={140} tick={{ fill: "#94a3b8", fontSize: 10 }} />
              <Tooltip />
              <Bar dataKey="value" fill="#3ee0c5" radius={[0, 8, 8, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </GlassCard>
      </div>
      <GlassCard title="Platform APIs">
        <p className="text-sm leading-6 text-slate-300">
          Paste an Instagram/X URL. FakeGuard will parse the username. It will not scrape the live
          profile.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <input value={url} onChange={(e) => setUrl(e.target.value)} className="input max-w-xl" />
          <button
            type="button"
            className="rounded-xl bg-accent px-4 py-2 text-sm font-semibold text-ink-950"
            onClick={() => void api.ingestUrl(url).then(setIngest).catch((err: Error) => setError(err.message))}
          >
            Parse URL
          </button>
        </div>
        {ingest && <p className="mt-3 text-sm text-slate-300">{String(ingest.detail || "")}</p>}
      </GlassCard>
      <GlassCard title="Continuous validation (analyst labels)">
        <p className="text-sm text-slate-400">
          After an analysis, mark it genuine or fake on the results page. Stored labels:{" "}
          {JSON.stringify(feedback?.counts || {})}
        </p>
        <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-400">
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

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="glass rounded-3xl p-4">
      <p className="text-xs uppercase tracking-[0.2em] text-slate-500">{label}</p>
      <p className="mt-2 font-display text-2xl">{value}</p>
    </div>
  );
}

function Cell({ title, value }: { title: string; value: number }) {
  return (
    <div className="rounded-2xl bg-white/5 p-4">
      <p className="text-xs text-slate-500">{title}</p>
      <p className="mt-1 font-display text-2xl">{value}</p>
    </div>
  );
}
