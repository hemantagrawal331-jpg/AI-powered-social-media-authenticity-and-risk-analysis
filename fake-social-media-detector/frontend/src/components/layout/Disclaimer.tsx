import { AlertTriangle } from "lucide-react";

export function Disclaimer() {
  return (
    <div className="mb-6 flex items-start gap-3 rounded-2xl border border-amber-400/20 bg-amber-400/5 px-4 py-3 text-sm text-amber-100/90">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-300" />
      <p>
        This analysis is probabilistic and should not be treated as proof that an account is fake,
        fraudulent, malicious, or automated. FakeGuard estimates patterns from voluntarily supplied
        observable signals and may produce false positives or false negatives. It does not require
        social-media credentials and does not access private account data.
      </p>
    </div>
  );
}
