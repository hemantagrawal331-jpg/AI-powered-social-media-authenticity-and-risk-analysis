import { useEffect, useState } from "react";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { GlassCard } from "../components/common/GlassCard";
import { RiskBadge } from "../components/common/RiskBadge";
import { ScoreBar } from "../components/common/ScoreBar";
import { useSamples } from "../hooks/useSamples";
import { api } from "../services/api";
import { type CompareResult, type ProfileInput } from "../types/analysis";

export function Compare() {
  const { samples } = useSamples();
  const [left, setLeft] = useState("genuine-personal");
  const [right, setRight] = useState("scam-giveaway");
  const [result, setResult] = useState<CompareResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [fromHistory, setFromHistory] = useState<string | null>(null);

  useEffect(() => {
    const raw = sessionStorage.getItem("fakeguard:compare-pair");
    if (!raw) return;
    sessionStorage.removeItem("fakeguard:compare-pair");
    try {
      const [accountA, accountB] = JSON.parse(raw) as [ProfileInput, ProfileInput];
      setFromHistory(`@${accountA.username} and @${accountB.username}`);
      setBusy(true);
      setError(null);
      api
        .compare(accountA, accountB)
        .then(setResult)
        .catch((err: Error) => setError(err.message))
        .finally(() => setBusy(false));
    } catch {
      setError("Saved comparison could not be read.");
    }
  }, []);

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
        <h1 className="font-display text-4xl tracking-tight">Compare</h1>
        <p className="mt-2 max-w-prose text-sm text-muted">Score two bundled samples, or a pair sent from history.</p>
      </div>
      <GlassCard>
        <div className="grid gap-4 md:grid-cols-[1fr_1fr_auto]">
          <Select label="Account A" value={left} onChange={setLeft} samples={samples} />
          <Select label="Account B" value={right} onChange={setRight} samples={samples} />
          <button
            type="button"
            onClick={() => void run()}
            disabled={busy}
            className="btn self-end"
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
                <p className="font-display text-5xl leading-none">{Math.round(item.fake_probability)}</p>
                <p className="mt-1 text-xs text-muted">Combined risk score, not a probability</p>
                <div className="mt-2">
                  <RiskBadge level={item.risk_level} />
                </div>
                <p className="mt-3 text-sm text-ink-soft">{item.purpose}</p>
                <div className="mt-4 space-y-3">
                  <ScoreBar label="Username risk" value={item.username_risk} />
                  <ScoreBar label="Bio risk" value={item.bio_risk} />
                  <ScoreBar label="Behavior risk" value={item.behavior_risk} />
                  <ScoreBar label="Overall risk" value={item.overall_risk} />
                </div>
                <dl className="mt-4 space-y-1 text-sm text-ink-soft">
                  <div className="flex justify-between">
                    <dt>Age (days)</dt>
                    <dd>{item.account_age_days ?? "—"}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt>Followers</dt>
                    <dd>{item.followers == null ? "—" : item.followers.toLocaleString()}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt>Avg likes</dt>
                    <dd>{item.average_likes ?? "—"}</dd>
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
            <ul className="list-disc space-y-2 pl-5 text-sm text-ink-soft">
              {result.differences.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </GlassCard>
        </>
      )}
      {!result && (
        <GlassCard>
          <p className="text-sm text-muted">
            Default comparison is a genuine personal account versus a scam/giveaway sample. You can
            also compare any two bundled profiles{fromHistory ? `, or the saved pair ${fromHistory}` : ""}.
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
      <span className="text-muted">{label}</span>
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
