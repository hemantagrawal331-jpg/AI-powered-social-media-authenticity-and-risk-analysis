import { GlassCard } from "../components/common/GlassCard";

export function About() {
  return (
    <div className="space-y-6">
      <h1 className="font-display text-3xl">About FakeGuard AI</h1>
      <GlassCard title="Problem">
        <p className="text-sm leading-6 text-slate-300">
          Fake social media accounts are used for scams, spam, impersonation, fake promotions, bot
          networks, phishing, misinformation, and fraud. People usually see only a username, a bio,
          and a follower count — not enough to judge trustworthiness.
        </p>
      </GlassCard>
      <GlassCard title="Solution">
        <p className="text-sm leading-6 text-slate-300">
          This prototype analyzes many weak signals together: profile completeness, username
          structure, engagement ratios, account age, posting behavior, bio language, content
          repetition, a basic image indicator, and neighborhood overlap with bundled samples. No
          single keyword or ratio is enough to brand an account malicious.
        </p>
      </GlassCard>
      <GlassCard title="Technology">
        <ul className="list-disc space-y-1 pl-5 text-sm text-slate-300">
          <li>Frontend: React, Vite, TypeScript, Tailwind CSS, Recharts, Lucide</li>
          <li>Backend: FastAPI, Pydantic, SQLAlchemy / SQLite, Pillow, ReportLab</li>
          <li>Model: Random Forest on 4,000 synthetic labeled profiles, blended with heuristics</li>
          <li>History: follower/like timelines, growth spikes, engagement collapse</li>
          <li>Validation: holdout accuracy/precision/recall plus analyst labels</li>
        </ul>
      </GlassCard>
      <GlassCard title="Limitations">
        <p className="text-sm leading-6 text-slate-300">
          Training data is synthetic, not a dump of live Instagram accounts. Official platform APIs
          are not connected because Meta/X require approved apps and prohibit scraping. A photo still
          does not prove identity. Open Model Lab for the current holdout metrics.
        </p>
      </GlassCard>
      <GlassCard title="How probability is computed now">
        <p className="text-sm leading-6 text-slate-300">
          Each analyzer still scores 0–100. A Random Forest, trained on those features plus
          historical timeline stats, outputs P(fake). The dashboard shows a blend: 62% model + 38%
          transparent heuristic weights. Analysts can label results to support later retraining.
        </p>
      </GlassCard>
    </div>
  );
}
