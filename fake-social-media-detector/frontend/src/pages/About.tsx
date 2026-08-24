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
          <li>Engine: modular heuristic scoring that can later wrap a trained model</li>
        </ul>
      </GlassCard>
      <GlassCard title="Limitations">
        <p className="text-sm leading-6 text-slate-300">
          The system does not scrape platforms, does not request login credentials, and does not
          claim identity verification from a photo. Scores are estimates from user-supplied or
          sample data. Accuracy in production would need labeled datasets, platform APIs, and
          ongoing validation.
        </p>
      </GlassCard>
      <GlassCard title="Future AI / ML upgrade">
        <p className="text-sm leading-6 text-slate-300">
          The analysis package is modular. The heuristic engine can be replaced or stacked with
          Random Forest or XGBoost on tabular features, NLP models for bios and captions, computer
          vision for profile photos, graph neural networks for clusters, anomaly detection for
          growth spikes, and official platform APIs when authorized.
        </p>
      </GlassCard>
    </div>
  );
}
