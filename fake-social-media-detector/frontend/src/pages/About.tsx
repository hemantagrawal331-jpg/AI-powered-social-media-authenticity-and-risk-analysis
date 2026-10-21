export function About() {
  return (
    <article className="max-w-3xl">
      <h1 className="font-display text-4xl tracking-tight sm:text-5xl">A desk for reading accounts, not a verdict machine.</h1>
      <p className="mt-6 text-base leading-7 text-ink-soft">
        Fake social accounts are used for scams, spam, impersonation, fake promotions, bot activity,
        phishing, and fraud. A person usually sees a username, a bio, and a follower count. FakeGuard
        is a place to put those observations next to a model and see which parts of the story the
        numbers actually support.
      </p>

      <section className="mt-12 border-t border-line pt-6">
        <h2 className="font-display text-3xl">What it estimates</h2>
        <p className="mt-4 text-sm leading-7 text-ink-soft">
          Authenticity, inauthenticity risk, confidence, evidence sufficiency, and uncertainty — from
          fields you type, a file you upload, a bundled sample, or a public page the server was asked
          to read. Missing data lowers confidence and drops that domain’s weight. It is never treated
          as proof of fraud.
        </p>
      </section>

      <section className="mt-10 border-t border-line pt-6">
        <h2 className="font-display text-3xl">How it is built</h2>
        <dl className="mt-4 divide-y divide-line border-y border-line text-sm">
          {[
            ["Interface", "React, Vite, TypeScript, Tailwind, Recharts."],
            ["Server", "FastAPI, Pydantic, SQLite, Pillow, ReportLab."],
            ["Model", "Calibrated random forest, histogram gradient boosting, logistic regression, isolation forest."],
            ["Fusion", "Evidence-weighted log-odds across identity, profile, engagement, time, content, network, language, and coordination."],
            ["Calibration", "Platt adjustment of the forest stack on synthetic validation. The combined risk score is a separate mix and is not that probability."],
            ["Out of distribution", "Isolation forest, centroid distance, and the pattern of missing features."],
          ].map(([term, detail]) => (
            <div key={term} className="grid gap-1 py-3 sm:grid-cols-[11rem_1fr]">
              <dt className="text-muted">{term}</dt>
              <dd>{detail}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="mt-10 border-t border-line pt-6">
        <h2 className="font-display text-3xl">Limits you should keep in view</h2>
        <p className="mt-4 text-sm leading-7 text-ink-soft">
          Training uses overlapping synthetic archetypes, not a live dump from any network. Official
          platform APIs are not connected. A photo does not prove identity. A fluent bio can fool a
          content-only check, so those checks are discounted. The metrics in Model lab are measured
          on synthetic holdout data. They are not a claim about accuracy on live Instagram or X.
        </p>
      </section>
    </article>
  );
}
