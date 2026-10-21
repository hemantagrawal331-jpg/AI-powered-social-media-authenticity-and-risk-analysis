import { useState } from "react";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { GlassCard } from "../components/common/GlassCard";
import {
  api,
  type DatasetCollect,
  type DatasetDetail,
  type DatasetHome,
  type DatasetReadiness,
} from "../services/api";

const TOKEN_KEY = "fakeguard:dataset-admin";

export function DatasetDesk() {
  const [token, setToken] = useState(() => sessionStorage.getItem(TOKEN_KEY) || "");
  const [draft, setDraft] = useState("");
  const [single, setSingle] = useState("");
  const [batch, setBatch] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [home, setHome] = useState<DatasetHome | null>(null);
  const [platform, setPlatform] = useState("");
  const [review, setReview] = useState("");
  const [report, setReport] = useState<DatasetCollect | null>(null);
  const [detail, setDetail] = useState<DatasetDetail | null>(null);
  const [readiness, setReadiness] = useState<DatasetReadiness | null>(null);
  const [form, setForm] = useState({
    review_label: "unknown",
    status: "unknown",
    genuine_kind: "verified_personal",
    harm: "none",
    fact_kind: "insufficient",
    evidence_quality: "insufficient",
    evidence_source: "",
    evidence_url: "",
    reviewer: "",
    rationale: "",
    disagreement: "",
    data_use: "do_not_train",
  });

  const load = async (nextToken = token, nextPlatform = platform, nextReview = review) => {
    const data = await api.dataset(nextToken, nextPlatform, nextReview);
    const ready = await api.datasetReadiness(nextToken);
    setHome(data);
    setReadiness(ready);
  };

  const unlock = async () => {
    setError(null);
    setBusy(true);
    try {
      sessionStorage.setItem(TOKEN_KEY, draft.trim());
      setToken(draft.trim());
      await load(draft.trim());
    } catch (err) {
      sessionStorage.removeItem(TOKEN_KEY);
      setToken("");
      setHome(null);
      setError(err instanceof Error ? err.message : "The dataset desk is locked.");
    } finally {
      setBusy(false);
    }
  };

  const collect = async (entries: string[]) => {
    setBusy(true);
    setError(null);
    setReport(null);
    try {
      const result = await api.datasetCollect(token, entries);
      setReport(result);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Collection failed");
    } finally {
      setBusy(false);
    }
  };

  const openRow = async (observationId: string) => {
    setError(null);
    try {
      setDetail(await api.datasetObservation(token, observationId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not open that observation");
    }
  };

  const saveReview = async () => {
    if (!detail) return;
    setBusy(true);
    setError(null);
    try {
      await api.datasetReview(token, { ...form, observation_id: detail.observation.observation_id });
      setDetail(await api.datasetObservation(token, detail.observation.observation_id));
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "The review was rejected");
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    if (!detail) return;
    setBusy(true);
    setError(null);
    try {
      await api.datasetDelete(token, detail.observation.account_key);
      setDetail(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setBusy(false);
    }
  };

  const download = async (fmt: "jsonl" | "csv") => {
    try {
      const blob = await api.datasetExport(token, fmt);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `github-public-v1.${fmt}`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed");
    }
  };

  const summary = home?.summary;

  return (
    <div className="space-y-4">
      <div>
        <p className="kicker">Dataset</p>
        <h1 className="mt-2 font-display text-4xl tracking-tight">GitHub collection desk</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">
          Fetch public GitHub profiles into the observation store. A successful fetch does not say the account is genuine or fraudulent.
        </p>
      </div>
      <div className="border border-caution/40 bg-caution/10 px-4 py-3 text-sm leading-6 text-ink-soft">
        Experimental — not validated on real-world accounts. Profile collection does not establish whether an account is genuine or fraudulent. Missing fields stay missing. The bundled demos are not part of this dataset.
      </div>
      <ErrorBanner message={error} />
      {!token && (
        <GlassCard title="Admin access">
          <p className="text-sm text-muted">
            Enter the server admin token. It stays in this browser session and is not built into the site. If the server has no ADMIN_TOKEN, collection stays locked.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <input
              type="password"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              className="input min-w-[16rem] flex-1"
              autoComplete="off"
            />
            <button type="button" className="btn" disabled={busy || !draft.trim()} onClick={() => void unlock()}>
              Unlock desk
            </button>
          </div>
        </GlassCard>
      )}
      {token && summary && (
        <>
          <GlassCard title="Store">
            <p className="text-sm text-ink-soft">{summary.storage_note}</p>
            <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-4">
              <Count label="Observations" value={summary.observations} />
              <Count label="Unique accounts" value={summary.unique_accounts} />
              <Count label="Unreviewed" value={summary.unreviewed} />
              <Count label="Unknown reviews" value={summary.unknown} />
              <Count label="Confirmed reviews" value={summary.by_review_state.confirmed || 0} />
              <Count label="Disagreements" value={summary.by_review_state.disagreement || 0} />
              <Count label="Provenance complete" value={summary.provenance_complete} />
              <Count label="Real-world metrics" value="none" />
            </dl>
            <p className="mt-3 text-xs text-muted">
              Platforms {JSON.stringify(summary.by_platform)} · labels {JSON.stringify(summary.by_label)} · schemas {summary.schema_versions.join(", ") || "—"} · {summary.observed_from || "no dates"} to {summary.observed_to || "—"}
            </p>
            <p className="mt-1 text-xs text-muted">
              Collection log: stored {summary.collection_log.stored || 0}, duplicates {summary.collection_log.duplicate || 0}, invalid {(summary.collection_log.invalid || 0) + (summary.collection_log.duplicate_in_batch || 0)}, errors {summary.collection_log.error || 0}, not attempted {summary.collection_log.not_attempted || 0}.
            </p>
            <div className="mt-3 flex gap-2">
              <button type="button" className="btn-ghost" onClick={() => void download("jsonl")}>
                Export JSONL
              </button>
              <button type="button" className="btn-ghost" onClick={() => void download("csv")}>
                Export CSV
              </button>
            </div>
          </GlassCard>
          <GlassCard title="Collect">
            <p className="text-sm text-muted">One profile, or up to five usernames or github.com user URLs. Entries are checked before any request. A rate limit stops the rest of the batch. Nothing is invented when a fetch fails.</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <input value={single} onChange={(event) => setSingle(event.target.value)} placeholder="octocat or https://github.com/octocat" className="input min-w-[16rem] flex-1" />
              <button type="button" className="btn" disabled={busy || !single.trim()} onClick={() => void collect([single.trim()])}>
                {busy ? "Fetching…" : "Fetch one profile"}
              </button>
            </div>
            <textarea
              value={batch}
              onChange={(event) => {
                setBatch(event.target.value);
                setConfirmed(false);
              }}
              placeholder={"one username or URL per line\nmaximum 5"}
              className="input mt-3 min-h-28 w-full"
            />
            <label className="mt-3 flex items-start gap-2 text-sm text-ink-soft">
              <input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} />
              I understand this batch only stores public fields. It does not label an account genuine, automated, or fraudulent.
            </label>
            <button
              type="button"
              className="btn mt-3"
              disabled={busy || !confirmed || !batch.trim()}
              onClick={() => void collect(batch.split("\n").map((line) => line.trim()).filter(Boolean))}
            >
              {busy ? "Fetching one at a time…" : "Start confirmed batch"}
            </button>
            {report && (
              <p className="mt-3 text-sm text-ink-soft">
                Stored {report.counts.stored || 0}. Duplicates {(report.counts.duplicate || 0) + (report.counts.duplicate_in_batch || 0)}. Invalid {report.counts.invalid || 0}. Failed {report.counts.error || 0}. Not attempted {report.counts.not_attempted || 0}.
              </p>
            )}
          </GlassCard>
          <GlassCard title="Observations">
            <div className="mb-3 flex flex-wrap gap-2">
              <select value={platform} onChange={(event) => { setPlatform(event.target.value); void load(token, event.target.value, review); }} className="input">
                <option value="">All platforms</option>
                <option value="github">GitHub</option>
              </select>
              <select value={review} onChange={(event) => { setReview(event.target.value); void load(token, platform, event.target.value); }} className="input">
                <option value="">All review states</option>
                <option value="unreviewed">Unreviewed</option>
                <option value="pending">Pending</option>
                <option value="confirmed">Confirmed</option>
                <option value="disagreement">Disagreement</option>
                <option value="unknown">Unknown</option>
              </select>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-[11px] uppercase tracking-wide text-muted">
                  <tr>
                    <th className="py-2">Account</th>
                    <th>Platform</th>
                    <th>Collected</th>
                    <th>Review</th>
                  </tr>
                </thead>
                <tbody>
                  {home.observations.map((row) => (
                    <tr key={row.observation_id} className="border-t border-line">
                      <td className="py-2">
                        <button type="button" className="underline decoration-line underline-offset-4" onClick={() => void openRow(row.observation_id)}>
                          {row.public_login}
                        </button>
                      </td>
                      <td>{row.platform}</td>
                      <td className="font-mono text-xs">{row.observed_at}</td>
                      <td>{row.review_state}</td>
                    </tr>
                  ))}
                  {home.observations.length === 0 && (
                    <tr>
                      <td colSpan={4} className="py-3 text-muted">No stored observations match these filters.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </GlassCard>
          {detail && (
            <GlassCard title={`@${detail.observation.public_login}`}>
              <p className="text-sm text-muted">Review state: {detail.review_state}. Schema {detail.observation.schema_version}. Source {detail.observation.source}.</p>
              <div className="mt-4 grid gap-4 lg:grid-cols-3">
                <FieldBlock title="Observed facts" rows={detail.fields.observed} />
                <FieldBlock title="Derived fields" rows={detail.fields.derived} />
                <FieldBlock title="Unavailable information" rows={detail.fields.unavailable} />
              </div>
              <p className="mt-4 text-sm text-ink-soft">Independently supported evidence is only what a reviewer stored below. A model score is not evidence.</p>
              {detail.reviews.length > 0 && (
                <ul className="mt-2 space-y-2 text-sm">
                  {detail.reviews.map((row, index) => (
                    <li key={index} className="border border-line p-2">
                      {String(row.review_label)} · {String(row.status)} · {String(row.evidence_source)} · {String(row.rationale || "")}
                    </li>
                  ))}
                </ul>
              )}
              <div className="mt-4 grid gap-2 sm:grid-cols-2">
                <select className="input" value={form.review_label} onChange={(event) => setForm({ ...form, review_label: event.target.value })}>
                  {["unknown", "genuine", "bot", "scam", "phishing", "impersonation"].map((label) => (
                    <option key={label}>{label}</option>
                  ))}
                </select>
                <select className="input" value={form.status} onChange={(event) => setForm({ ...form, status: event.target.value })}>
                  {["unknown", "suspected", "confirmed"].map((label) => (
                    <option key={label}>{label}</option>
                  ))}
                </select>
                {form.review_label === "genuine" && (
                  <select className="input" value={form.genuine_kind} onChange={(event) => setForm({ ...form, genuine_kind: event.target.value })}>
                    <option value="verified_personal">verified personal</option>
                    <option value="verified_organization">verified organization</option>
                    <option value="legitimate_promotion">legitimate promotion</option>
                  </select>
                )}
                {form.review_label === "bot" && (
                  <select className="input" value={form.harm} onChange={(event) => setForm({ ...form, harm: event.target.value })}>
                    <option value="none">automation, harm not claimed</option>
                    <option value="malicious">malicious automation</option>
                  </select>
                )}
                <select className="input" value={form.fact_kind} onChange={(event) => setForm({ ...form, fact_kind: event.target.value })}>
                  <option value="insufficient">insufficient fact</option>
                  <option value="platform_verified">platform-verified fact</option>
                  <option value="reviewer_inference">reviewer inference</option>
                </select>
                <select className="input" value={form.evidence_quality} onChange={(event) => setForm({ ...form, evidence_quality: event.target.value })}>
                  {["insufficient", "low", "moderate", "high"].map((label) => (
                    <option key={label}>{label}</option>
                  ))}
                </select>
                <input className="input" placeholder="Evidence source" value={form.evidence_source} onChange={(event) => setForm({ ...form, evidence_source: event.target.value })} />
                <input className="input" placeholder="https evidence URL, when required" value={form.evidence_url} onChange={(event) => setForm({ ...form, evidence_url: event.target.value })} />
                <input className="input" placeholder="Reviewer initials" value={form.reviewer} onChange={(event) => setForm({ ...form, reviewer: event.target.value })} />
                <input className="input" placeholder="Disagreement, if reviewers conflict" value={form.disagreement} onChange={(event) => setForm({ ...form, disagreement: event.target.value })} />
                <textarea className="input min-h-24 sm:col-span-2" placeholder="Rationale" value={form.rationale} onChange={(event) => setForm({ ...form, rationale: event.target.value })} />
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <button type="button" className="btn" disabled={busy} onClick={() => void saveReview()}>
                  Save review
                </button>
                <button type="button" className="btn-ghost" disabled={busy} onClick={() => void remove()}>
                  Delete account from local store
                </button>
              </div>
            </GlassCard>
          )}
          {readiness && (
            <GlassCard title="Evaluation readiness">
              <p className="text-sm leading-6 text-ink-soft">{readiness.note}</p>
              <p className="mt-2 font-mono text-xs text-muted">
                Confirmed accounts {readiness.confirmed_accounts} / count milestone {readiness.count_milestone}. Metrics withheld. Training {String(readiness.training_performed)}. Split leakage {String(readiness.split_leakage)}.
              </p>
            </GlassCard>
          )}
        </>
      )}
    </div>
  );
}

function Count({ label, value }: { label: string; value: number | string }) {
  return (
    <div>
      <dt className="text-[11px] uppercase tracking-wide text-muted">{label}</dt>
      <dd className="mt-1 font-mono">{value}</dd>
    </div>
  );
}

function fieldText(row: { value: unknown; status: string }) {
  if (row.status !== "observed" || row.value == null) return "unavailable";
  if (row.value === "") return "observed empty";
  return String(row.value);
}

function FieldBlock({ title, rows }: { title: string; rows: { name: string; value: unknown; note?: string; status: string }[] }) {
  return (
    <div>
      <p className="text-[11px] uppercase tracking-wide text-muted">{title}</p>
      <ul className="mt-2 space-y-1 text-sm text-ink-soft">
        {rows.map((row) => (
          <li key={row.name}>
            {row.name}: {fieldText(row)}
            {row.note ? ` — ${row.note}` : ""}
          </li>
        ))}
      </ul>
    </div>
  );
}
