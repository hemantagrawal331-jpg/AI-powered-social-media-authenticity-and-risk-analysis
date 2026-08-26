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
          FakeGuard is a multimodal authenticity intelligence system. It estimates authenticity
          probability, inauthenticity risk, model confidence, evidence sufficiency, and uncertainty
          from voluntarily supplied fields. Missing data lowers confidence and drops domain weights
          — it is never treated as proof of fraud.
        </p>
      </GlassCard>
      <GlassCard title="Technology">
        <ul className="list-disc space-y-1 pl-5 text-sm text-slate-300">
          <li>Frontend: React, Vite, TypeScript, Tailwind CSS, Recharts, Lucide</li>
          <li>Backend: FastAPI, Pydantic, SQLAlchemy / SQLite, Pillow, ReportLab</li>
          <li>Ensemble: calibrated Random Forest + histogram gradient boosting + logistic + isolation forest</li>
          <li>Fusion: evidence-weighted log-odds with Botometer-style domain families</li>
          <li>Calibration: isotonic (Platt fallback), ECE and Brier reported in Model Lab</li>
        </ul>
      </GlassCard>
      <GlassCard title="Limitations">
        <p className="text-sm leading-6 text-slate-300">
          Training uses overlapping synthetic archetypes, not live Instagram dumps. Official platform
          APIs are not connected. A photo does not prove identity. LLM-written bios can fool
          content-only checks; those checks are discounted. Open Model Lab and MODEL_CARD.md for
          measured synthetic metrics — they are not live-platform accuracy.
        </p>
      </GlassCard>
    </div>
  );
}
