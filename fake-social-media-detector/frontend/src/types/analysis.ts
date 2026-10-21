export type Platform = "instagram" | "twitter" | "x" | "facebook" | "tiktok" | "linkedin" | "youtube" | "other";

export interface ProfileInput {
  username: string;
  platform: Platform;
  display_name: string;
  profile_url: string;
  followers: number | null;
  following: number | null;
  posts: number | null;
  account_age_days: number | null;
  bio: string;
  verified: boolean;
  has_profile_picture: boolean | null;
  external_links: number | null;
  profile_fields_completed: number | null;
  total_profile_fields: number;
  average_likes: number | null;
  average_comments: number | null;
  average_shares: number | null;
  posting_frequency_per_week: number | null;
  has_external_link: boolean;
  captions: string[];
  hashtags: string[];
  recent_activity: { date: string; event: string; magnitude: number }[];
  follower_growth_events: { date: string; delta: number }[];
  following_growth_events: { date: string; delta: number }[];
  engagement_history: { date: string; likes: number; comments: number; followers: number }[];
  image_base64?: string | null;
  image_filename?: string | null;
  sample_id?: string | null;
  private_account?: boolean;
  source_note?: string;
  post_timestamps?: string[];
  follower_usernames?: string[];
  comment_samples?: string[];
}

export interface FeatureBreakdown {
  name: string;
  value: number | string;
  risk_level: string;
  explanation: string;
  score: number;
}

export interface ReasonItem {
  title: string;
  severity: string;
  score_contribution: number;
  explanation: string;
}

export interface PurposeItem {
  label: string;
  confidence: number;
}

export interface Recommendation {
  title: string;
  detail: string;
  priority: string;
}

export interface TimelineEvent {
  date: string;
  title: string;
  detail: string;
  severity: string;
}

export interface ChartPoint {
  label: string;
  value: number;
}

export interface EngagementSeriesPoint {
  date: string;
  followers: number;
  likes: number;
  comments: number;
}

export interface ImageAnalysis {
  present: boolean;
  confidence_indicator: number;
  resolution: string;
  flags: string[];
  explanation: string;
  prototype_note: string;
}

export interface ClusterInfo {
  detected: boolean;
  cluster_id: string | null;
  size: number;
  risk: number;
  title: string;
  explanation: string;
  shared_signals: string[];
  members: string[];
}

export interface ImpersonationInfo {
  detected: boolean;
  similarity: number;
  matched_account: string | null;
  matched_display_name: string | null;
  explanation: string;
  signals: string[];
  prototype_note: string;
}

export interface NetworkNode {
  id: string;
  label: string;
  group: string;
  risk: number;
}

export interface NetworkEdge {
  source: string;
  target: string;
  relation: string;
}

export interface NetworkInfo {
  risk: string;
  explanation: string;
  nodes: NetworkNode[];
  edges: NetworkEdge[];
  prototype_note: string;
}

export interface FeatureScores {
  profile: number;
  username: number;
  engagement: number;
  follower_ratio: number;
  account_age: number;
  behavior: number;
  bio: number;
  content: number;
  image: number;
}

export interface ScoreContribution {
  feature: string;
  weight: number;
  raw_score: number;
  weighted_score: number;
}

export interface AnalysisResult {
  id?: number | null;
  username: string;
  display_name: string;
  platform: string;
  profile_url: string;
  fake_probability: number;
  risk_level: string;
  purpose: string;
  purpose_confidence: number;
  top_purposes: PurposeItem[];
  feature_scores: FeatureScores;
  score_contributions: ScoreContribution[];
  reasons: ReasonItem[];
  recommendations: Recommendation[];
  behaviors: FeatureBreakdown[];
  profile_features: FeatureBreakdown[];
  engagement_metrics: Record<string, unknown>;
  username_analysis: Record<string, unknown>;
  bio_analysis: Record<string, unknown>;
  image_analysis: ImageAnalysis;
  timeline: TimelineEvent[];
  radar: ChartPoint[];
  engagement_series: EngagementSeriesPoint[];
  network: NetworkInfo;
  cluster: ClusterInfo;
  impersonation: ImpersonationInfo;
  model?: {
    source: string;
    algorithm: string;
    ml_probability: number | null;
    heuristic_probability: number | null;
    logistic_probability?: number | null;
    anomaly_probability?: number | null;
    available: boolean;
    calibration?: string;
    model_version?: string;
    feature_schema?: string;
    analysis_engine?: string;
    probability_meaning?: string;
    combined_score_meaning?: string;
  };
  history_signals?: Record<string, unknown>;
  authenticity_score?: number;
  inauthenticity_probability?: number;
  classification?: string;
  confidence?: string;
  uncertainty?: number;
  uncertainty_label?: string;
  uncertainty_interval?: number;
  evidence_sufficiency?: number;
  ood_score?: number;
  domain_scores?: Record<
    string,
    {
      score: number;
      risk: number;
      confidence: number;
      evidence_count: number;
      missing_data_ratio: number;
      explanations: string[];
    }
  >;
  top_positive_signals?: {
    signal_name: string;
    direction: string;
    strength: number;
    domain: string;
    statistical_evidence: string;
    human_explanation: string;
    observed?: string;
    expected?: string;
  }[];
  top_risk_signals?: {
    signal_name: string;
    direction: string;
    strength: number;
    domain: string;
    statistical_evidence: string;
    human_explanation: string;
    observed?: string;
    expected?: string;
  }[];
  evidence_waterfall?: { label: string; delta: number; value: number; kind: string }[];
  counterfactuals?: string[];
  explanation?: string;
  limitations?: string[];
  signal_hardness?: { hard_to_fake?: number; easy_to_fake_with_llm?: number };
  language_analysis?: Record<string, unknown>;
  coordination?: {
    coordination_score?: number;
    category?: string;
    explanation?: string;
    pairs?: { a: string; b: string; score: number }[];
  };
  interval_stats?: Record<string, number>;
  input_hash?: string;
  disclaimer: string;
  created_at: string;
}

export interface HistoryItem {
  id: number;
  username: string;
  platform: string;
  risk_level: string;
  purpose: string;
  fake_probability: number;
  created_at: string;
}

export interface SampleSummary {
  id: string;
  label: string;
  category: string;
  username: string;
  platform: string;
  description: string;
}

export interface ReportMeta {
  id: number;
  analysis_id: number;
  username: string;
  format: string;
  created_at: string;
}

export interface CompareResult {
  account_a: AnalysisResult;
  account_b: AnalysisResult;
  summary: {
    username: string;
    platform: string;
    fake_probability: number;
    risk_level: string;
    purpose: string;
    account_age_days: number | null;
    followers: number | null;
    following: number | null;
    average_likes: number | null;
    engagement_rate: number;
    username_risk: number;
    bio_risk: number;
    behavior_risk: number;
    overall_risk: number;
  }[];
  differences: string[];
}

export interface RetrievedField {
  name: string;
  status: "observed" | "unavailable" | string;
  provider: string;
  observed_at: string;
  mapped_to_model?: boolean;
  value?: unknown;
  detail?: string;
}

export interface PublicProfileFetch {
  fetched: boolean;
  login_required: boolean;
  notes: string;
  run_id: string | null;
  profile: Partial<ProfileInput>;
  provider?: string;
  model_status?: string;
  retrieved_at?: string;
  fields?: RetrievedField[];
}

export const emptyProfile = (): ProfileInput => ({
  username: "",
  platform: "instagram",
  display_name: "",
  profile_url: "",
  followers: null,
  following: null,
  posts: null,
  account_age_days: null,
  bio: "",
  verified: false,
  has_profile_picture: null,
  external_links: null,
  profile_fields_completed: null,
  total_profile_fields: 8,
  average_likes: null,
  average_comments: null,
  average_shares: null,
  posting_frequency_per_week: null,
  has_external_link: false,
  captions: [],
  hashtags: [],
  recent_activity: [],
  follower_growth_events: [],
  following_growth_events: [],
  engagement_history: [],
});
