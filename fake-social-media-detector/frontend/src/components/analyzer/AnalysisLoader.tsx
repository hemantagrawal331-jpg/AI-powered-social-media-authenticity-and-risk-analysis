import { useEffect, useState } from "react";
import { Check, LoaderCircle } from "lucide-react";

const STEPS = [
  "Scanning profile metadata...",
  "Analyzing username structure...",
  "Checking engagement anomalies...",
  "Reviewing behavioral patterns...",
  "Scoring bio and content language...",
  "Calculating weighted risk score...",
  "Classifying likely account purpose...",
  "Generating report artifacts...",
];

export function AnalysisLoader() {
  const [step, setStep] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setStep((current) => (current < STEPS.length - 1 ? current + 1 : current));
    }, 420);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <div className="glass mx-auto max-w-xl rounded-3xl p-8">
      <p className="font-display text-xl">Analyzing profile...</p>
      <p className="mt-1 text-sm text-slate-400">Heuristic engine is scoring supplied signals. No live platform call.</p>
      <ul className="mt-6 space-y-3">
        {STEPS.map((label, index) => {
          const done = index < step;
          const active = index === step;
          return (
            <li key={label} className="flex items-center gap-3 text-sm">
              {done ? (
                <Check className="h-4 w-4 text-accent" />
              ) : (
                <LoaderCircle className={`h-4 w-4 ${active ? "animate-spin text-accent" : "text-slate-600"}`} />
              )}
              <span className={done || active ? "text-slate-100" : "text-slate-500"}>{label}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
