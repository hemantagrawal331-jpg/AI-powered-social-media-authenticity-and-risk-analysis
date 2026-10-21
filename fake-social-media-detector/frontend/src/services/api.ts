import type {
  AnalysisResult,
  CompareResult,
  HistoryItem,
  ProfileInput,
  PublicProfileFetch,
  ReportMeta,
  SampleSummary,
} from "../types/analysis";

const BASE = import.meta.env.VITE_API_URL?.replace(/\/$/, "") || "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, {
      ...init,
      headers: {
        ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
        ...(init?.headers || {}),
      },
    });
  } catch {
    throw new Error("Backend unavailable. Start the FastAPI server on port 8000.");
  }

  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    const contentType = response.headers.get("content-type") || "";
    try {
      if (contentType.includes("application/json")) {
        const payload = await response.json();
        if (typeof payload.detail === "string") detail = payload.detail;
        else if (Array.isArray(payload.detail)) {
          detail = payload.detail.map((item: { msg?: string }) => item.msg || "Invalid field").join("; ");
        }
      } else {
        detail = "Backend API did not return JSON. Wait for the latest Vercel deploy to finish, then retry."
      }
    } catch {
      /* keep default */
    }
    throw new Error(detail);
  }

  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    throw new Error(
      "Backend API did not return JSON. Wait for the latest Vercel deploy to finish, then retry.",
    );
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string; tinyfish_configured?: boolean }>("/api/health"),
  samples: () => request<SampleSummary[]>("/api/samples"),
  sample: (id: string) => request<{ id: string; profile: ProfileInput }>(`/api/samples/${id}`),
  analyze: (profile: ProfileInput) =>
    request<AnalysisResult>("/api/analyze", { method: "POST", body: JSON.stringify(profile) }),
  analyzeUpload: async (file: File, image?: File | null) => {
    const body = new FormData();
    body.append("file", file);
    if (image) body.append("image", image);
    return request<AnalysisResult>("/api/analyze/upload", { method: "POST", body });
  },
  history: () => request<HistoryItem[]>("/api/history"),
  historyItem: (id: number) => request<AnalysisResult>(`/api/history/${id}`),
  historyInput: (id: number) => request<ProfileInput>(`/api/history/${id}/input`),
  deleteHistory: (id: number) => request<{ deleted: number }>(`/api/history/${id}`, { method: "DELETE" }),
  compare: (account_a: ProfileInput, account_b: ProfileInput) =>
    request<CompareResult>("/api/compare", {
      method: "POST",
      body: JSON.stringify({ account_a, account_b }),
    }),
  reports: () => request<ReportMeta[]>("/api/reports"),
  createReport: (analysisId: number, fmt: "json" | "pdf" = "json") =>
    request<ReportMeta>(`/api/reports/${analysisId}?fmt=${fmt}`, { method: "POST" }),
  reportDownloadUrl: (reportId: number) => `${BASE}/api/reports/${reportId}/download`,
  networkOverview: () => request<Record<string, unknown>>("/api/network/overview"),
  modelStatus: () => request<Record<string, unknown>>("/api/model"),
  modelFeedback: (body: {
    analysis_id?: number | null;
    username: string;
    predicted_fake: number;
    analyst_label: "fake" | "genuine";
    note?: string;
  }) => request<{ id: number; stored: boolean }>("/api/model/feedback", { method: "POST", body: JSON.stringify(body) }),
  modelFeedbackList: () => request<{ counts: Record<string, number>; items: Record<string, unknown>[] }>("/api/model/feedback"),
  ingestUrl: (url: string) => request<Record<string, unknown>>("/api/ingest/url", { method: "POST", body: JSON.stringify({ url }) }),
  fetchPublicProfile: (url: string) =>
    request<PublicProfileFetch>("/api/profile/fetch", { method: "POST", body: JSON.stringify({ url }) }),
  dataset: (token: string, platform = "", review = "") =>
    request<DatasetHome>(`/api/dataset?platform=${encodeURIComponent(platform)}&review=${encodeURIComponent(review)}`, {
      headers: { Authorization: `Bearer ${token}` },
    }),
  datasetCollect: (token: string, entries: string[]) =>
    request<DatasetCollect>("/api/dataset/collect", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify({ entries, confirm: true }),
    }),
  datasetObservation: (token: string, observationId: string) =>
    request<DatasetDetail>(`/api/dataset/observations/${observationId}`, {
      headers: { Authorization: `Bearer ${token}` },
    }),
  datasetReview: (token: string, body: Record<string, string>) =>
    request<{ result: string; review_state: string; metrics: null }>("/api/dataset/reviews", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
    }),
  datasetDelete: (token: string, accountKey: string) =>
    request<{ observations_removed: number; labels_removed: number }>(
      `/api/dataset/accounts/${accountKey}?confirm=true`,
      { method: "DELETE", headers: { Authorization: `Bearer ${token}` } },
    ),
  datasetReadiness: (token: string) =>
    request<DatasetReadiness>("/api/dataset/readiness", { headers: { Authorization: `Bearer ${token}` } }),
  datasetExport: async (token: string, fmt: "jsonl" | "csv") => {
    const response = await fetch(`${BASE}/api/dataset/export?fmt=${fmt}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(typeof payload.detail === "string" ? payload.detail : `Export failed (${response.status})`);
    }
    return response.blob();
  },
};

export interface DatasetHome {
  observations: DatasetRow[];
  summary: DatasetSummary;
}

export interface DatasetRow {
  observation_id: string;
  account_key: string;
  platform: string;
  public_login: string;
  observed_at: string;
  schema_version: string;
  source: string;
  review_state: string;
}

export interface DatasetSummary {
  observations: number;
  unique_accounts: number;
  by_platform: Record<string, number>;
  by_review_state: Record<string, number>;
  by_label: Record<string, number>;
  unreviewed: number;
  unknown: number;
  collection_log: Record<string, number>;
  observed_from: string | null;
  observed_to: string | null;
  schema_versions: string[];
  provenance_complete: number;
  demos_included: boolean;
  durable: boolean;
  storage_note: string;
  storage?: {
    backend: string;
    durable: boolean;
    healthy: boolean;
    mode: string;
    last_write_at: string | null;
    migration_status: string;
    message: string;
  };
  real_world_metrics: null;
}

export interface DatasetCollect {
  counts: Record<string, number>;
  results: { input: string; result: string; detail?: string; observation_id?: string }[];
  stored_profiles_are_labels: boolean;
  metrics: null;
}

export interface DatasetField {
  name: string;
  status: string;
  value: unknown;
  note?: string;
}

export interface DatasetDetail {
  observation: DatasetRow;
  fields: { observed: DatasetField[]; unavailable: DatasetField[]; derived: DatasetField[] };
  reviews: Record<string, unknown>[];
  review_state: string;
  collection_is_not_a_label: boolean;
}

export interface DatasetReadiness {
  confirmed_accounts: number;
  count_milestone: number;
  count_milestone_met: boolean;
  metrics: null;
  real_world_metrics: null;
  evaluation_performed: boolean;
  training_performed: boolean;
  split_leakage: boolean;
  note: string;
}

export function persistFetch(data: PublicProfileFetch | null) {
  if (!data) {
    sessionStorage.removeItem("fakeguard:last-fetch");
    return;
  }
  sessionStorage.setItem("fakeguard:last-fetch", JSON.stringify(data));
}

export function readPersistedFetch(): PublicProfileFetch | null {
  const raw = sessionStorage.getItem("fakeguard:last-fetch");
  if (!raw) return null;
  try {
    return JSON.parse(raw) as PublicProfileFetch;
  } catch {
    return null;
  }
}

export function persistResult(result: AnalysisResult) {
  sessionStorage.setItem("fakeguard:last", JSON.stringify(result));
}

export function readPersistedResult(): AnalysisResult | null {
  const raw = sessionStorage.getItem("fakeguard:last");
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AnalysisResult;
  } catch {
    return null;
  }
}
