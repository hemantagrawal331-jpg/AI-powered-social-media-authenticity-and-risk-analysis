import { AlertTriangle } from "lucide-react";

export function Disclaimer() {
  return (
    <div className="mb-6 flex items-start gap-3 rounded-2xl border border-amber-400/20 bg-amber-400/5 px-4 py-3 text-sm text-amber-100/90">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-300" />
      <p>
        This tool provides an estimated risk score based on available profile signals and heuristic
        analysis. It cannot guarantee that an account is fake or genuine. Real-world accuracy would
        require large-scale training data, platform APIs, historical behavior, and continuous model
        validation.
      </p>
    </div>
  );
}
