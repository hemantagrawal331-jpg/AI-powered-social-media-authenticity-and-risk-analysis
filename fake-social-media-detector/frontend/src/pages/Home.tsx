import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { RiskBadge } from "../components/common/RiskBadge";
import { api, persistResult } from "../services/api";

const concerns = [
  ["Fake identity", "A profile that presents as a real person with almost no history behind it."],
  ["Impersonation", "A lookalike of a person or brand, used to borrow trust."],
  ["Scam offers", "Giveaways, investment pitches, or payment requests that do not match the account."],
  ["Phishing", "A profile whose job is to move someone to a suspicious link."],
  ["Bots", "Posting and engagement that look scheduled rather than personal."],
  ["Coordination", "Several accounts repeating the same offer or narrative."],
  ["Spam", "The same promotional text, posted again and again."],
  ["Engagement games", "Follower or like counts that do not match the visible activity."],
];

const findings = [
  {
    label: "Observed",
    title: "Account is 18 days old",
    detail: "The bundled profile reports 25,400 followers and 45 posts in that window.",
  },
  {
    label: "Observed",
    title: "Bio asks for a payment",
    detail: "“Send 0.1 ETH get 2 ETH back.” That is the text in the sample, not a live page.",
  },
  {
    label: "Interpretation",
    title: "Engagement does not match the audience",
    detail: "Average likes are 80. The model treats that gap as a risk signal, not as proof.",
  },
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
      setError(err instanceof Error ? err.message : "The sample investigation did not run.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-20">
      <section className="grid items-start gap-12 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)] lg:gap-16">
        <div className="lg:pt-4">
          <p className="kicker">Investigative desk</p>
          <h1 className="mt-4 max-w-[12ch] font-display text-5xl leading-[0.95] tracking-tight sm:text-6xl">
            See what the signal is hiding.
          </h1>
          <p className="mt-6 max-w-prose text-base leading-7 text-ink-soft">
            Investigate suspicious social content, understand account credibility, and explore risk
            signals with evidence you can examine.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <button type="button" className="btn" onClick={() => navigate("/analyze")}>
              Analyze a post
            </button>
            <button type="button" className="btn-ghost" disabled={busy} onClick={() => void runSample("scam-giveaway")}>
              {busy ? "Scoring sample…" : "Explore a sample investigation"}
            </button>
          </div>
          <p className="mt-4 text-sm text-muted">
            <button type="button" className="underline decoration-line underline-offset-4 hover:text-ink" disabled={busy} onClick={() => void runSample("genuine-personal")}>
              Lower-risk personal sample
            </button>
            <span className="px-2">/</span>
            <button type="button" className="underline decoration-line underline-offset-4 hover:text-ink" disabled={busy} onClick={() => void runSample("fake-bot")}>
              Bundled bot sample
            </button>
          </p>
          <ErrorBanner message={error} />
        </div>

        <figure className="border border-line bg-paper-raised">
          <figcaption className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
            <span className="kicker">Demonstration</span>
            <span className="text-[11px] text-muted">Bundled sample · not a live read</span>
          </figcaption>
          <div className="grid gap-0 md:grid-cols-[1.1fr_0.9fr]">
            <div className="border-b border-line p-4 md:border-b-0 md:border-r">
              <p className="font-mono text-xs text-muted">@crypto_giveaway_9283 · X</p>
              <p className="mt-3 font-display text-2xl leading-tight">Official Crypto Giveaway</p>
              <p className="mt-3 text-sm leading-6 text-ink-soft">
                FREE BITCOIN GIVEAWAY! Send 0.1 ETH get 2 ETH back! Official Elon giveaway. Act now!!!
                Click the link
              </p>
              <dl className="mt-5 grid grid-cols-3 gap-3 border-t border-line pt-4 text-sm">
                <div>
                  <dt className="text-[11px] uppercase tracking-wide text-muted">Age</dt>
                  <dd className="mt-1 font-mono">18d</dd>
                </div>
                <div>
                  <dt className="text-[11px] uppercase tracking-wide text-muted">Followers</dt>
                  <dd className="mt-1 font-mono">25,400</dd>
                </div>
                <div>
                  <dt className="text-[11px] uppercase tracking-wide text-muted">Avg likes</dt>
                  <dd className="mt-1 font-mono">80</dd>
                </div>
              </dl>
            </div>
            <div className="p-4">
              <p className="kicker">Sample reading</p>
              <p className="mt-2 font-display text-5xl leading-none">67</p>
              <p className="mt-1 text-xs text-muted">Illustrative inauthenticity risk, 0–100. Run the sample for the model’s number.</p>
              <div className="mt-3">
                <RiskBadge level="High risk" />
              </div>
              <ol className="mt-5 space-y-3">
                {findings.map((item) => (
                  <li key={item.title} className="border-t border-line pt-3">
                    <p className="text-[11px] uppercase tracking-[0.14em] text-muted">{item.label}</p>
                    <p className="mt-1 text-sm font-medium">{item.title}</p>
                    <p className="mt-1 text-xs leading-5 text-muted">{item.detail}</p>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        </figure>
      </section>

      <section>
        <div className="grid gap-8 border-t border-line pt-8 lg:grid-cols-[16rem_1fr]">
          <h2 className="font-display text-3xl tracking-tight">How an investigation moves</h2>
          <ol className="divide-y divide-line border-y border-line">
            {[
              ["01", "Submit something you can stand behind", "A public profile URL, a username and the fields you know, a JSON file, or one of the bundled samples. Passwords are never requested."],
              ["02", "The model scores those fields", "Identity, profile, engagement, timing, content, and any network notes are fused. Missing fields lower confidence. They are not treated as fraud."],
              ["03", "Read the result as evidence plus interpretation", "You get a risk level, an uncertainty range, and the observations behind them. A score is not a finding of intent."],
              ["04", "Compare, export, or correct it", "History stores the analysis locally. You can compare two cases, download a report, or label the result for later retraining."],
            ].map(([index, title, copy]) => (
              <li key={index} className="grid gap-2 py-4 sm:grid-cols-[3rem_14rem_1fr] sm:gap-6">
                <span className="font-mono text-xs text-muted">{index}</span>
                <p className="font-medium">{title}</p>
                <p className="text-sm leading-6 text-muted">{copy}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="grid gap-10 border-t border-line pt-8 lg:grid-cols-[16rem_1fr]">
        <h2 className="font-display text-3xl tracking-tight">What people are usually trying to judge</h2>
        <dl className="grid gap-x-10 gap-y-6 sm:grid-cols-2">
          {concerns.map(([title, copy]) => (
            <div key={title} className="border-t border-line pt-3">
              <dt className="font-medium">{title}</dt>
              <dd className="mt-1 text-sm leading-6 text-muted">{copy}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="grid gap-10 border-t border-line pt-8 md:grid-cols-2">
        <div>
          <h2 className="font-display text-3xl tracking-tight">What the score is</h2>
          <p className="mt-4 max-w-prose text-sm leading-7 text-ink-soft">
            The result has two different numbers. The model-estimated probability is the Platt-adjusted
            chance of the inauthentic class, fit on synthetic validation data. The combined risk score
            mixes that estimate with rules and is not a calibrated probability that an account is fake.
            Domain weights fall to zero when that domain has no data. Open Model lab for the synthetic
            holdout metrics. Those numbers are not live-platform accuracy.
          </p>
        </div>
        <div>
          <h2 className="font-display text-3xl tracking-tight">What it will not do</h2>
          <p className="mt-4 max-w-prose text-sm leading-7 text-ink-soft">
            It will not log into Instagram, X, or any other network. A public-page fetch, when the
            server has a key, only reads a page anyone can open and fills the form. It does not
            decide that someone is a criminal. You still have to read the evidence.
          </p>
        </div>
      </section>
    </div>
  );
}
