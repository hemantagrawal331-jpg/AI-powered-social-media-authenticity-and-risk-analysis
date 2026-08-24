export type Platform = "instagram" | "twitter" | "facebook" | "tiktok" | "linkedin";

export interface ProfileInput {
  username: string;
  platform: Platform;
  display_name: string;
  profile_url: string;
  followers: number;
  following: number;
  posts: number;
  account_age_days: number;
  bio: string;
  verified: boolean;
  has_profile_picture: boolean;
  external_links: number;
  profile_fields_completed: number;
  total_profile_fields: number;
  average_likes: number;
  average_comments: number;
  average_shares: number;
  posting_frequency_per_week: number;
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
    account_age_days: number;
    followers: number;
    following: number;
    average_likes: number;
    engagement_rate: number;
    username_risk: number;
    bio_risk: number;
    behavior_risk: number;
    overall_risk: number;
  }[];
  differences: string[];
}

export const emptyProfile = (): ProfileInput => ({
  username: "",
  platform: "instagram",
  display_name: "",
  profile_url: "",
  followers: 0,
  following: 0,
  posts: 0,
  account_age_days: 180,
  bio: "",
  verified: false,
  has_profile_picture: true,
  external_links: 0,
  profile_fields_completed: 5,
  total_profile_fields: 8,
  average_likes: 0,
  average_comments: 0,
  average_shares: 0,
  posting_frequency_per_week: 2,
  has_external_link: false,
  captions: [],
  hashtags: [],
  recent_activity: [],
  follower_growth_events: [],
  following_growth_events: [],
  engagement_history: [],
});
