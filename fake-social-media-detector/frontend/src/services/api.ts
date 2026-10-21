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
};

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
