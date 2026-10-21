import { LoaderCircle } from "lucide-react";

const STAGES = [
  "Feature extraction across identity, profile, engagement, time, content, and network",
  "Calibrated ensemble: forest, boosting, logistic baseline, isolation forest",
  "Evidence-weighted fusion, then a written explanation",
];

export function AnalysisLoader() {
  return (
    <div className="max-w-xl border border-line bg-paper-raised p-6 sm:p-8" role="status" aria-live="polite">
      <div className="flex items-center gap-3">
        <LoaderCircle className="h-4 w-4 animate-spin" />
        <p className="font-display text-2xl">Scoring the fields you submitted</p>
      </div>
      <p className="mt-3 text-sm leading-6 text-muted">
        The server is running the model now. The list below is the pipeline. Individual stages are
        not reported back separately, so this is not a live scan.
      </p>
      <ol className="mt-6 space-y-3 border-t border-line pt-4 text-sm">
        {STAGES.map((label, index) => (
          <li key={label} className="grid grid-cols-[2rem_1fr] gap-2">
            <span className="font-mono text-xs text-muted">0{index + 1}</span>
            <span>{label}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}
