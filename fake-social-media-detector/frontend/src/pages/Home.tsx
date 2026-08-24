import {
  Bot,
  Fingerprint,
  Megaphone,
  Network,
  ShieldAlert,
  Siren,
  Users,
  Wallet,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { GlassCard } from "../components/common/GlassCard";
import { api, persistResult } from "../services/api";
import { useState } from "react";
import { ErrorBanner } from "../components/common/ErrorBanner";

const insights = [
  { title: "Fake Identity", copy: "Accounts pretending to be real people with thin history.", icon: Fingerprint },
  { title: "Bot Networks", copy: "Automated accounts operating in coordinated clusters.", icon: Bot },
  { title: "Scam Accounts", copy: "Profiles promoting fraudulent money or crypto offers.", icon: Wallet },
  { title: "Impersonation", copy: "Lookalikes of people or brands used to steal trust.", icon: ShieldAlert },
  { title: "Spam", copy: "Repetitive promotional or irrelevant content at scale.", icon: Megaphone },
  { title: "Engagement Manipulation", copy: "Artificial likes, followers, and comments.", icon: Users },
  { title: "Phishing", copy: "Accounts that redirect people to suspicious links.", icon: Siren },
  { title: "Coordinated Campaigns", copy: "Many accounts repeating the same narrative or offer.", icon: Network },
];

export function Home() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const runSample = async (id: string) => {
    setBusy(true);
    setError(null);
    try {
      const sample = await api.sample(id);
      const result = await api.analyze(sample.profile);
      persistResult(result);
      navigate("/results");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Demo failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-8">
      <section className="glass overflow-hidden rounded-[32px] px-6 py-10 sm:px-10">
        <p className="text-xs uppercase tracking-[0.28em] text-accent">FakeGuard AI</p>
        <h1 className="mt-3 max-w-3xl font-display text-4xl font-semibold leading-tight sm:text-5xl">
          AI-powered social media authenticity and risk analysis
        </h1>
        <p className="mt-4 max-w-2xl text-slate-300">
          Estimate whether an account looks genuine, suspicious, or fake by combining username,
          engagement, bio, behavior, content, and network signals — without logging into any
          platform.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <button
            type="button"
            disabled={busy}
            onClick={() => void runSample("scam-giveaway")}
            className="rounded-2xl bg-accent px-5 py-3 font-display text-sm font-semibold text-ink-950"
          >
            Launch Demo
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => void runSample("genuine-personal")}
            className="rounded-2xl border border-white/10 px-5 py-3 text-sm"
          >
            Try Genuine Account
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => void runSample("fake-bot")}
            className="rounded-2xl border border-white/10 px-5 py-3 text-sm"
          >
            Try Suspicious Account
          </button>
          <button type="button" onClick={() => navigate("/analyze")} className="rounded-2xl bg-white/10 px-5 py-3 text-sm">
            Analyze Account
          </button>
        </div>
        <ErrorBanner message={error} />
      </section>

      <section>
        <h2 className="mb-4 font-display text-2xl">Problem insights</h2>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {insights.map(({ title, copy, icon: Icon }) => (
            <button
              key={title}
              type="button"
              className="glass group rounded-3xl p-5 text-left transition hover:-translate-y-1 hover:shadow-glow"
              onClick={() => navigate("/about")}
            >
              <Icon className="h-5 w-5 text-accent" />
              <p className="mt-3 font-display font-semibold">{title}</p>
              <p className="mt-1 text-sm text-slate-400">{copy}</p>
            </button>
          ))}
        </div>
      </section>

      <GlassCard title="How the prototype scores risk">
        <p className="text-sm leading-6 text-slate-300">
          FakeGuard AI does not call Instagram, X, or any paid API. You supply profile fields (or
          load a sample). The backend extracts features, normalizes each signal to 0–100, then
          applies documented weights: engagement 20%, behavior 15%, and smaller weights for
          username, bio, content, ratio, age, completeness, and image. Changing the inputs changes
          the score, charts, reasons, and purpose estimate.
        </p>
      </GlassCard>
    </div>
  );
}
