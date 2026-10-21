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
        <p>No analysis yet.</p>
        <Link to="/analyze" className="mt-3 inline-block text-sm underline decoration-line underline-offset-4">
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
      {notice && <div className="border border-line bg-paper-raised px-4 py-2 text-sm">{notice}</div>}

      <section className="border-b border-line pb-8">
        <div className="flex flex-wrap items-end justify-between gap-8">
          <div>
            <p className="kicker">Case</p>
            <h1 className="mt-2 font-display text-4xl tracking-tight sm:text-5xl">@{result.username}</h1>
            <p className="mt-2 font-mono text-sm text-muted">
              {result.platform}
              {result.display_name ? ` · ${result.display_name}` : ""}
            </p>
            <div className="mt-4">
              <RiskBadge level={result.risk_level} />
            </div>
          </div>
          <div className="min-w-[10rem]">
            <p className="kicker">Authenticity</p>
            <p className="mt-1 font-display text-6xl leading-none">
              {Math.round(result.authenticity_score ?? 100 - result.fake_probability)}
            </p>
            <p className="mt-2 text-xs text-muted">out of 100 · higher looks more genuine</p>
          </div>
        </div>
        <p className="mt-6 max-w-3xl text-sm leading-7 text-ink-soft">
            {result.explanation ||
            `Combined risk score is ${Math.round(result.fake_probability)} on a 0–100 scale. This is a relative risk indicator, not the percentage chance the account is fake.`}
        </p>
        <dl className="mt-6 grid gap-4 border-y border-line py-4 text-sm sm:grid-cols-4">
          <div>
            <dt className="text-[11px] uppercase tracking-wide text-muted">Combined risk score</dt>
            <dd className="mt-1 font-mono">{Math.round(result.inauthenticity_probability ?? result.fake_probability)}</dd>
            <dd className="mt-1 text-xs text-muted">Relative indicator, not the chance the account is fake.</dd>
          </div>
          <div>
            <dt className="text-[11px] uppercase tracking-wide text-muted">Model confidence</dt>
            <dd className="mt-1 font-mono">{result.confidence ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-[11px] uppercase tracking-wide text-muted">Uncertainty</dt>
            <dd className="mt-1 font-mono">
              {result.uncertainty_label ?? "—"} ±{result.uncertainty_interval ?? 12}%
            </dd>
          </div>
          <div>
            <dt className="text-[11px] uppercase tracking-wide text-muted">Evidence sufficiency</dt>
            <dd className="mt-1 font-mono">{Math.round(result.evidence_sufficiency ?? 0)}%</dd>
          </div>
        </dl>
        <p className="mt-4 text-sm">
          Likely purpose: <span className="font-medium">{result.purpose}</span>
          <span className="text-muted"> · {result.purpose_confidence}% estimated confidence, not a definitive claim</span>
        </p>
        <p className="mt-3 font-mono text-[11px] leading-5 text-muted">
          Model {result.model?.model_version || "v2.1.0"} · schema {result.model?.feature_schema || "v2.1"} ·{" "}
          {result.model?.analysis_engine || "hybrid-ensemble"} · calibration {result.model?.calibration || "platt"}
          {result.input_hash ? ` · input ${result.input_hash}` : ""}
        </p>
        {result.model?.available && (
          <p className="mt-1 text-xs text-muted">
            Model-estimated P(inauthentic class) {result.model.ml_probability ?? "—"} · Platt-adjusted on the synthetic validation split, not the combined score.
            Rules {result.model.heuristic_probability ?? "—"} · logistic {result.model.logistic_probability ?? "—"} · anomaly {result.model.anomaly_probability ?? "—"}, uncalibrated.
          </p>
        )}
        <div className="mt-6 flex flex-wrap gap-3">
          <button type="button" onClick={() => void download("pdf")} className="btn">
            Download report
          </button>
          <button type="button" onClick={() => void download("json")} className="btn-ghost">
            Download JSON
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
            <p className="mt-4 text-xs text-muted">
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
              <div key={signal.signal_name} className="border border-verified/20 bg-verified/5 p-3 text-sm">
                <p className="font-medium text-verified">Supports a genuine reading. {signal.human_explanation}</p>
                <p className="mt-1 text-xs text-muted">{signal.statistical_evidence}</p>
              </div>
            ))}
            {(result.top_risk_signals || []).slice(0, 4).map((signal) => (
              <div key={signal.signal_name} className="border border-caution/20 bg-caution/5 p-3 text-sm">
                <p className="font-medium text-caution">Raises risk. {signal.human_explanation}</p>
                <p className="mt-1 text-xs text-muted">
                  Observed {signal.observed || "—"} · expected {signal.expected || "—"} · {signal.statistical_evidence}
                </p>
              </div>
            ))}
          </div>
        </GlassCard>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <GlassCard title="Language consistency">
          <p className="text-sm text-ink-soft">
            {String((result.language_analysis?.explanations as string[] | undefined)?.[0] || "No language text was supplied.")}
          </p>
          <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
            <Row label="Bio language" value={String(result.language_analysis?.bio_language ?? "—")} />
            <Row label="Multilingual" value={result.language_analysis?.multilingual ? "yes" : "no"} />
            <Row label="Abrupt switch" value={result.language_analysis?.abrupt_switch ? "yes" : "no"} />
            <Row label="Consistency" value={`${Math.round(Number(result.language_analysis?.consistency ?? 0) * 100)}%`} />
          </dl>
        </GlassCard>
        <GlassCard title="Coordination">
          <p className="font-display text-lg">{(result.coordination?.category || "LOW_COORDINATION").replaceAll("_", " ")}</p>
          <p className="mt-2 text-sm text-ink-soft">{result.coordination?.explanation || "Single-account analysis only."}</p>
          <p className="mt-3 font-mono text-xs text-muted">
            score {Math.round((result.coordination?.coordination_score || 0) * 100)} / 100
          </p>
        </GlassCard>
      </div>

      {!!result.interval_stats && Number(result.interval_stats.n || 0) >= 2 && (
        <GlassCard title="Inter-post interval statistics">
          <dl className="grid gap-2 text-sm sm:grid-cols-3">
            <Row label="Mean interval" value={num(result.interval_stats.mean)} />
            <Row label="Median" value={num(result.interval_stats.median)} />
            <Row label="Std. dev." value={num(result.interval_stats.std)} />
            <Row label="CV" value={num(result.interval_stats.cv)} />
            <Row label="Burstiness" value={num(result.interval_stats.burstiness)} />
            <Row label="Autocorr" value={num(result.interval_stats.autocorr)} />
          </dl>
          <p className="mt-3 text-xs text-muted">
            Burstiness B = (σ − μ) / (σ + μ). High periodicity is evidence of scheduling, not proof of inauthenticity.
          </p>
        </GlassCard>
      )}

      {!!result.counterfactuals?.length && (
        <GlassCard title="What would reduce this risk?">
          <ul className="list-disc space-y-2 pl-5 text-sm text-ink-soft">
            {result.counterfactuals.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-muted">Model-based counterfactual estimates, not advice to manipulate a live profile.</p>
        </GlassCard>
      )}

      <GlassCard title="Why we think this account is suspicious">
        <div className="space-y-3">
          {result.reasons.map((reason) => (
            <div key={reason.title} className="border border-line p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-medium">
                  <span className="mr-2 font-mono text-[11px] uppercase tracking-wide text-muted">{reason.severity}</span>
                  {reason.title}
                </p>
                <span className="font-mono text-xs text-muted">contrib {reason.score_contribution}</span>
              </div>
              <p className="mt-1 text-sm text-ink-soft">{reason.explanation}</p>
            </div>
          ))}
        </div>
      </GlassCard>

      <div className="grid gap-4 lg:grid-cols-3">
        <GlassCard title="Likely account purpose">
          <p className="text-xs text-muted">Estimated classification, not a definitive claim.</p>
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
          <p className="mt-3 text-sm text-muted">{String(metrics.explanation || "")}</p>
        </GlassCard>
        <GlassCard title="Username & bio">
          <p className="text-sm">
            Username risk: <strong>{String(username.score ?? 0)}</strong>/100
          </p>
          <p className="mt-2 text-sm text-muted">{String(username.explanation || "")}</p>
          <p className="mt-4 text-sm">
            Bio risk: <strong>{String(bio.score ?? 0)}</strong>/100
          </p>
          <p className="mt-2 text-sm text-muted">{String(bio.explanation || "")}</p>
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
                  <p className="text-muted">{item.explanation}</p>
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
                <span className="text-muted">{item.name}</span>
                <span>{String(item.value)}</span>
              </div>
            ))}
          </div>
        </GlassCard>
      </div>

      <GlassCard title="Suspicious activity timeline">
        <ol className="relative space-y-4 border-l border-line pl-6">
          {result.timeline.map((event) => (
            <li key={`${event.date}-${event.title}`}>
              <span className="absolute -left-[5px] mt-1.5 h-2 w-2 rounded-full bg-ink" />
              <p className="font-mono text-xs text-muted">{event.date}</p>
              <p className="font-medium">{event.title}</p>
              <p className="text-sm text-muted">{event.detail}</p>
            </li>
          ))}
        </ol>
      </GlassCard>

      <div className="grid gap-4 lg:grid-cols-2">
        <GlassCard title="Profile image confidence indicator">
          <p className="font-display text-3xl">{result.image_analysis.confidence_indicator}</p>
          <p className="mt-2 text-sm text-ink-soft">{result.image_analysis.explanation}</p>
          <p className="mt-3 text-xs text-muted">{result.image_analysis.prototype_note}</p>
        </GlassCard>
        <GlassCard title="Recommendations">
          <ul className="space-y-3">
            {result.recommendations.map((item) => (
              <li key={item.title}>
                <p className="font-medium">{item.title}</p>
                <p className="text-sm text-muted">{item.detail}</p>
              </li>
            ))}
          </ul>
        </GlassCard>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <GlassCard title="Possible impersonation detection">
          <p className="text-sm text-muted">{result.impersonation.prototype_note}</p>
          <p className="mt-3 font-display text-xl">
            {result.impersonation.detected ? "Possible impersonation detected" : "No strong impersonation match"}
          </p>
          <p className="mt-1 text-sm">Similarity: {result.impersonation.similarity}%</p>
          <p className="mt-2 text-sm text-ink-soft">{result.impersonation.explanation}</p>
        </GlassCard>
        <GlassCard title="Bot / suspicious cluster detection">
          <p className="font-display text-xl">{result.cluster.title}</p>
          {result.cluster.detected && (
            <p className="mt-2 text-sm">
              Cluster size: {result.cluster.size} · Risk: {result.cluster.risk}%
            </p>
          )}
          <p className="mt-2 text-sm text-ink-soft">{result.cluster.explanation}</p>
        </GlassCard>
      </div>

      <GlassCard title="Weighted score contributions">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-muted">
              <tr>
                <th className="pb-2">Feature</th>
                <th>Weight</th>
                <th>Raw 0–100</th>
                <th>Weighted</th>
              </tr>
            </thead>
            <tbody>
              {result.score_contributions.map((row) => (
                <tr key={row.feature} className="border-t border-line">
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
          <p className="text-sm text-ink-soft">{String(result.history_signals.explanation || "")}</p>
          <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
            <Row label="History risk" value={String(result.history_signals.score ?? "—")} />
            <Row label="Like volatility" value={String(result.history_signals.like_cv ?? "—")} />
            <Row label="Follower velocity" value={String(result.history_signals.follower_velocity ?? "—")} />
            <Row label="Engagement collapse" value={String(result.history_signals.engagement_divergence ?? "—")} />
          </dl>
        </GlassCard>
      )}

      <GlassCard title="Continuous validation">
        <p className="text-sm text-muted">Mark this result so the model can be retrained later.</p>
        <div className="mt-3 flex gap-2">
          <button
            type="button"
            className="btn-ghost"
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
            className="btn-ghost"
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
      <dt className="text-muted">{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function num(value: unknown) {
  if (typeof value !== "number") return "—";
  return value.toFixed(2);
}

