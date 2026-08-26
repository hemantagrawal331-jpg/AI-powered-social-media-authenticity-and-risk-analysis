import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { DashboardCharts } from "../components/charts/DashboardCharts";
import { EvidenceWaterfall } from "../components/charts/EvidenceWaterfall";
import { RiskGauge } from "../components/charts/RiskGauge";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { GlassCard } from "../components/common/GlassCard";
import { RiskBadge } from "../components/common/RiskBadge";
import { ScoreBar } from "../components/common/ScoreBar";
import { api, persistResult, readPersistedResult } from "../services/api";
import type { AnalysisResult } from "../types/analysis";

export function Results() {
  const { id } = useParams();
  const [result, setResult] = useState<AnalysisResult | null>(readPersistedResult());
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    api
      .historyItem(Number(id))
      .then((item) => {
        persistResult(item);
        setResult(item);
      })
      .catch((err: Error) => setError(err.message));
  }, [id]);

  const download = async (fmt: "json" | "pdf") => {
    if (!result?.id) {
      setError("Save an analysis first — run Analyze Account so a history id exists.");
      return;
    }
    try {
      const report = await api.createReport(result.id, fmt);
      window.open(api.reportDownloadUrl(report.id), "_blank");
      setNotice(`${fmt.toUpperCase()} report generated.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Report failed");
    }
  };

  if (!result) {
    return (
      <GlassCard>
        <p className="text-slate-300">No analysis yet.</p>
        <Link to="/analyze" className="mt-3 inline-block text-accent">
          Open the analyzer
        </Link>
      </GlassCard>
    );
  }

  const metrics = result.engagement_metrics;
  const username = result.username_analysis;
  const bio = result.bio_analysis;

  return (
    <div className="space-y-6">
      <ErrorBanner message={error} />
      {notice && <div className="rounded-2xl border border-accent/20 bg-accent/10 px-4 py-2 text-sm">{notice}</div>}

      <section className="glass rounded-[32px] px-6 py-8 text-center">
        <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Social account intelligence</p>
        <p className="mt-3 font-mono text-sm text-slate-400">
          @{result.username} · {result.platform}
        </p>
        <p className="mt-6 text-sm text-slate-300">Authenticity score</p>
        <p className="mt-1 font-display text-7xl font-bold">{Math.round(result.authenticity_score ?? 100 - result.fake_probability)}</p>
        <p className="text-sm text-slate-500">/ 100</p>
        <div className="mt-3 flex justify-center">
          <RiskBadge level={result.risk_level} />
        </div>
        <p className="mx-auto mt-4 max-w-2xl text-sm leading-6 text-slate-300">
          {result.explanation ||
            `Based on the observable evidence provided, this account shows an estimated ${Math.round(result.fake_probability)}% probability of elevated inauthenticity risk.`}
        </p>
        <dl className="mx-auto mt-6 grid max-w-3xl gap-3 text-xs sm:grid-cols-4">
          <div className="rounded-2xl border border-white/5 bg-white/5 px-3 py-2">
            <dt className="text-slate-500">Inauthenticity risk</dt>
            <dd className="mt-1 font-mono text-base text-slate-100">{Math.round(result.inauthenticity_probability ?? result.fake_probability)}%</dd>
          </div>
          <div className="rounded-2xl border border-white/5 bg-white/5 px-3 py-2">
            <dt className="text-slate-500">Model confidence</dt>
            <dd className="mt-1 font-mono text-base text-slate-100">{result.confidence ?? "—"}</dd>
          </div>
          <div className="rounded-2xl border border-white/5 bg-white/5 px-3 py-2">
            <dt className="text-slate-500">Uncertainty</dt>
            <dd className="mt-1 font-mono text-base text-slate-100">
              {result.uncertainty_label ?? "—"} ±{result.uncertainty_interval ?? 12}%
            </dd>
          </div>
          <div className="rounded-2xl border border-white/5 bg-white/5 px-3 py-2">
            <dt className="text-slate-500">Evidence sufficiency</dt>
            <dd className="mt-1 font-mono text-base text-slate-100">{Math.round(result.evidence_sufficiency ?? 0)}%</dd>
          </div>
        </dl>
        <p className="mt-4 text-slate-200">
          Likely purpose: <span className="text-accent">{result.purpose}</span> · {result.purpose_confidence}%
          estimated confidence
        </p>
        {result.model?.available && (
          <p className="mt-2 text-xs text-slate-500">
            {result.model.model_version || "v2"} · {result.model.analysis_engine || "hybrid ensemble"} · calibration{" "}
            {result.model.calibration || "isotonic"} · RF {result.model.ml_probability ?? "—"}% · rules{" "}
            {result.model.heuristic_probability ?? "—"}%
          </p>
        )}
        <div className="mt-6 flex justify-center gap-3">
          <button type="button" onClick={() => void download("json")} className="rounded-xl border border-white/10 px-4 py-2 text-sm">
            Download JSON
          </button>
          <button type="button" onClick={() => void download("pdf")} className="rounded-xl bg-accent px-4 py-2 text-sm font-semibold text-ink-950">
            Download Report
          </button>
        </div>
      </section>

      <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
        <GlassCard>
          <RiskGauge value={result.fake_probability} />
        </GlassCard>
        <GlassCard title="Domain authenticity">
          <div className="space-y-4">
            {Object.entries(result.domain_scores || {}).map(([name, card]) => (
              <ScoreBar key={name} label={name} value={card.score} />
            ))}
            {!result.domain_scores && (
              <>
                <ScoreBar label="Username" value={result.feature_scores.username} />
                <ScoreBar label="Engagement" value={result.feature_scores.engagement} />
                <ScoreBar label="Behavior" value={result.feature_scores.behavior} />
                <ScoreBar label="Bio" value={result.feature_scores.bio} />
                <ScoreBar label="Content" value={result.feature_scores.content} />
                <ScoreBar label="Profile" value={result.feature_scores.profile} />
              </>
            )}
          </div>
          {result.signal_hardness && (
            <p className="mt-4 text-xs text-slate-500">
              Score mix from hard-to-fake metadata/behavior/graph: {result.signal_hardness.hard_to_fake}% ·
              LLM-easy content/media: {result.signal_hardness.easy_to_fake_with_llm}%
            </p>
          )}
        </GlassCard>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <GlassCard title="Evidence waterfall">
          <EvidenceWaterfall result={result} />
        </GlassCard>
        <GlassCard title="Why this result">
          <div className="space-y-3">
            {(result.top_positive_signals || []).slice(0, 4).map((signal) => (
              <div key={signal.signal_name} className="rounded-2xl border border-emerald-400/10 bg-emerald-400/5 p-3 text-sm">
                <p className="font-medium text-emerald-200">✓ {signal.human_explanation}</p>
                <p className="mt-1 text-xs text-slate-500">{signal.statistical_evidence}</p>
              </div>
            ))}
            {(result.top_risk_signals || []).slice(0, 4).map((signal) => (
              <div key={signal.signal_name} className="rounded-2xl border border-amber-400/10 bg-amber-400/5 p-3 text-sm">
                <p className="font-medium text-amber-100">⚠ {signal.human_explanation}</p>
                <p className="mt-1 text-xs text-slate-500">
                  Observed {signal.observed || "—"} · expected {signal.expected || "—"} · {signal.statistical_evidence}
                </p>
              </div>
            ))}
          </div>
        </GlassCard>
      </div>

      {!!result.counterfactuals?.length && (
        <GlassCard title="What would reduce this risk?">
          <ul className="list-disc space-y-2 pl-5 text-sm text-slate-300">
            {result.counterfactuals.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-slate-500">Model-based counterfactual estimates, not advice to manipulate a live profile.</p>
        </GlassCard>
      )}

      <GlassCard title="Why we think this account is suspicious">
        <div className="space-y-3">
          {result.reasons.map((reason) => (
            <div key={reason.title} className="rounded-2xl border border-white/5 bg-white/5 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-medium">
                  {reason.severity === "high" ? "🔴" : reason.severity === "medium" ? "🟠" : "🟢"} {reason.title}
                </p>
                <span className="font-mono text-xs text-slate-400">contrib {reason.score_contribution}</span>
              </div>
              <p className="mt-1 text-sm text-slate-300">{reason.explanation}</p>
            </div>
          ))}
        </div>
      </GlassCard>

      <div className="grid gap-4 lg:grid-cols-3">
        <GlassCard title="Likely account purpose">
          <p className="text-xs text-slate-500">Estimated classification, not a definitive claim.</p>
          <div className="mt-4 space-y-3">
            {result.top_purposes.map((item) => (
              <ScoreBar key={item.label} label={item.label} value={item.confidence} />
            ))}
          </div>
        </GlassCard>
        <GlassCard title="Engagement snapshot">
          <dl className="space-y-2 text-sm">
            <Row label="Average likes" value={String(metrics.average_likes ?? "—")} />
            <Row label="Average comments" value={String(metrics.average_comments ?? "—")} />
            <Row label="Engagement rate" value={`${metrics.engagement_rate ?? 0}%`} />
            <Row label="Likes / followers" value={`${metrics.likes_to_followers_ratio ?? 0}%`} />
            <Row label="Comments / likes" value={`${metrics.comments_to_likes_ratio ?? 0}%`} />
            <Row label="Engagement risk" value={String(metrics.risk_level ?? "—")} />
          </dl>
          <p className="mt-3 text-sm text-slate-400">{String(metrics.explanation || "")}</p>
        </GlassCard>
        <GlassCard title="Username & bio">
          <p className="text-sm">
            Username risk: <strong>{String(username.score ?? 0)}</strong>/100
          </p>
          <p className="mt-2 text-sm text-slate-400">{String(username.explanation || "")}</p>
          <p className="mt-4 text-sm">
            Bio risk: <strong>{String(bio.score ?? 0)}</strong>/100
          </p>
          <p className="mt-2 text-sm text-slate-400">{String(bio.explanation || "")}</p>
        </GlassCard>
      </div>

      <DashboardCharts result={result} />

      <div className="grid gap-4 lg:grid-cols-2">
        <GlassCard title="Account behavior">
          <div className="space-y-3">
            {result.behaviors.map((item) => (
              <div key={item.name} className="flex items-start justify-between gap-3 text-sm">
                <div>
                  <p className="font-medium">{item.name}</p>
                  <p className="text-slate-400">{item.explanation}</p>
                </div>
                <RiskBadge level={item.risk_level} />
              </div>
            ))}
          </div>
        </GlassCard>
        <GlassCard title="Profile features">
          <div className="space-y-2 text-sm">
            {result.profile_features.map((item) => (
              <div key={item.name} className="flex justify-between gap-3">
                <span className="text-slate-400">{item.name}</span>
                <span>{String(item.value)}</span>
              </div>
            ))}
          </div>
        </GlassCard>
      </div>

      <GlassCard title="Suspicious activity timeline">
        <ol className="relative space-y-4 border-l border-white/10 pl-6">
          {result.timeline.map((event) => (
            <li key={`${event.date}-${event.title}`}>
              <span className="absolute -left-1.5 mt-1.5 h-3 w-3 rounded-full bg-accent" />
              <p className="font-mono text-xs text-slate-500">{event.date}</p>
              <p className="font-medium">{event.title}</p>
              <p className="text-sm text-slate-400">{event.detail}</p>
            </li>
          ))}
        </ol>
      </GlassCard>

      <div className="grid gap-4 lg:grid-cols-2">
        <GlassCard title="Profile image confidence indicator">
          <p className="font-display text-3xl">{result.image_analysis.confidence_indicator}</p>
          <p className="mt-2 text-sm text-slate-300">{result.image_analysis.explanation}</p>
          <p className="mt-3 text-xs text-slate-500">{result.image_analysis.prototype_note}</p>
        </GlassCard>
        <GlassCard title="Recommendations">
          <ul className="space-y-3">
            {result.recommendations.map((item) => (
              <li key={item.title}>
                <p className="font-medium">{item.title}</p>
                <p className="text-sm text-slate-400">{item.detail}</p>
              </li>
            ))}
          </ul>
        </GlassCard>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <GlassCard title="Possible impersonation detection">
          <p className="text-sm text-slate-400">{result.impersonation.prototype_note}</p>
          <p className="mt-3 font-display text-xl">
            {result.impersonation.detected ? "Possible impersonation detected" : "No strong impersonation match"}
          </p>
          <p className="mt-1 text-sm">Similarity: {result.impersonation.similarity}%</p>
          <p className="mt-2 text-sm text-slate-300">{result.impersonation.explanation}</p>
        </GlassCard>
        <GlassCard title="Bot / suspicious cluster detection">
          <p className="font-display text-xl">{result.cluster.title}</p>
          {result.cluster.detected && (
            <p className="mt-2 text-sm">
              Cluster size: {result.cluster.size} · Risk: {result.cluster.risk}%
            </p>
          )}
          <p className="mt-2 text-sm text-slate-300">{result.cluster.explanation}</p>
        </GlassCard>
      </div>

      <GlassCard title="Weighted score contributions">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-slate-400">
              <tr>
                <th className="pb-2">Feature</th>
                <th>Weight</th>
                <th>Raw 0–100</th>
                <th>Weighted</th>
              </tr>
            </thead>
            <tbody>
              {result.score_contributions.map((row) => (
                <tr key={row.feature} className="border-t border-white/5">
                  <td className="py-2">{row.feature}</td>
                  <td>{Math.round(row.weight * 100)}%</td>
                  <td>{row.raw_score}</td>
                  <td>{row.weighted_score}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </GlassCard>

      {result.history_signals && (
        <GlassCard title="Historical behavior">
          <p className="text-sm text-slate-300">{String(result.history_signals.explanation || "")}</p>
          <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
            <Row label="History risk" value={String(result.history_signals.score ?? "—")} />
            <Row label="Like volatility" value={String(result.history_signals.like_cv ?? "—")} />
            <Row label="Follower velocity" value={String(result.history_signals.follower_velocity ?? "—")} />
            <Row label="Engagement collapse" value={String(result.history_signals.engagement_divergence ?? "—")} />
          </dl>
        </GlassCard>
      )}

      <GlassCard title="Continuous validation">
        <p className="text-sm text-slate-400">Mark this result so the model can be retrained later.</p>
        <div className="mt-3 flex gap-2">
          <button
            type="button"
            className="rounded-xl border border-emerald-400/30 px-4 py-2 text-sm"
            onClick={() =>
              void api
                .modelFeedback({
                  analysis_id: result.id,
                  username: result.username,
                  predicted_fake: result.fake_probability,
                  analyst_label: "genuine",
                })
                .then(() => setNotice("Labeled genuine. Stored for later retraining."))
                .catch((err: Error) => setError(err.message))
            }
          >
            Label genuine
          </button>
          <button
            type="button"
            className="rounded-xl border border-rose-400/30 px-4 py-2 text-sm"
            onClick={() =>
              void api
                .modelFeedback({
                  analysis_id: result.id,
                  username: result.username,
                  predicted_fake: result.fake_probability,
                  analyst_label: "fake",
                })
                .then(() => setNotice("Labeled fake. Stored for later retraining."))
                .catch((err: Error) => setError(err.message))
            }
          >
            Label fake
          </button>
        </div>
      </GlassCard>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-slate-400">{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

