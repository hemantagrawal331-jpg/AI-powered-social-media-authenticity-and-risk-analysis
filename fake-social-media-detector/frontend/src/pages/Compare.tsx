import { useState } from "react";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { GlassCard } from "../components/common/GlassCard";
import { RiskBadge } from "../components/common/RiskBadge";
import { ScoreBar } from "../components/common/ScoreBar";
import { useSamples } from "../hooks/useSamples";
import { api } from "../services/api";
import { emptyProfile, type CompareResult, type ProfileInput } from "../types/analysis";

export function Compare() {
  const { samples } = useSamples();
  const [left, setLeft] = useState("genuine-personal");
  const [right, setRight] = useState("scam-giveaway");
  const [result, setResult] = useState<CompareResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const run = async () => {
    setBusy(true);
    setError(null);
    try {
      const [a, b] = await Promise.all([api.sample(left), api.sample(right)]);
      const compared = await api.compare(a.profile as ProfileInput, b.profile as ProfileInput);
      setResult(compared);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Compare failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl">Account comparison</h1>
        <p className="mt-1 text-sm text-slate-400">Side-by-side scoring of two sample or analyzed profiles.</p>
      </div>
      <GlassCard>
        <div className="grid gap-4 md:grid-cols-[1fr_1fr_auto]">
          <Select label="Account A" value={left} onChange={setLeft} samples={samples} />
          <Select label="Account B" value={right} onChange={setRight} samples={samples} />
          <button
            type="button"
            onClick={() => void run()}
            disabled={busy}
            className="self-end rounded-2xl bg-accent px-5 py-3 text-sm font-semibold text-ink-950"
          >
            {busy ? "Comparing..." : "Compare"}
          </button>
        </div>
      </GlassCard>
      <ErrorBanner message={error} />
      {result && (
        <>
          <div className="grid gap-4 lg:grid-cols-2">
            {result.summary.map((item) => (
              <GlassCard key={item.username} title={`@${item.username}`}>
                <p className="font-display text-4xl">{Math.round(item.fake_probability)}%</p>
                <div className="mt-2">
                  <RiskBadge level={item.risk_level} />
                </div>
                <p className="mt-3 text-sm text-slate-300">{item.purpose}</p>
                <div className="mt-4 space-y-3">
                  <ScoreBar label="Username risk" value={item.username_risk} />
                  <ScoreBar label="Bio risk" value={item.bio_risk} />
                  <ScoreBar label="Behavior risk" value={item.behavior_risk} />
                  <ScoreBar label="Overall risk" value={item.overall_risk} />
                </div>
                <dl className="mt-4 space-y-1 text-sm text-slate-300">
                  <div className="flex justify-between">
                    <dt>Age (days)</dt>
                    <dd>{item.account_age_days}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt>Followers</dt>
                    <dd>{item.followers.toLocaleString()}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt>Avg likes</dt>
                    <dd>{item.average_likes}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt>Engagement rate</dt>
                    <dd>{item.engagement_rate}%</dd>
                  </div>
                </dl>
              </GlassCard>
            ))}
          </div>
          <GlassCard title="Differences">
            <ul className="list-disc space-y-2 pl-5 text-sm text-slate-300">
              {result.differences.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </GlassCard>
        </>
      )}
      {!result && (
        <GlassCard>
          <p className="text-sm text-slate-400">
            Default comparison is a genuine personal account versus a scam/giveaway sample. You can
            also compare any two bundled profiles. Empty fallback: {emptyProfile().username || "manual profiles via Analyzer."}
          </p>
        </GlassCard>
      )}
    </div>
  );
}

function Select({
  label,
  value,
  onChange,
  samples,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  samples: { id: string; label: string }[];
}) {
  return (
    <label className="block space-y-1 text-sm">
      <span className="text-slate-400">{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)} className="input">
        {samples.map((sample) => (
          <option key={sample.id} value={sample.id}>
            {sample.label}
          </option>
        ))}
      </select>
    </label>
  );
}
