import { AlertTriangle } from "lucide-react";

export function Disclaimer() {
  return (
    <div className="mb-6 flex items-start gap-3 rounded-2xl border border-amber-400/20 bg-amber-400/5 px-4 py-3 text-sm text-amber-100/90">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-300" />
      <p>
        FakeGuard estimates risk with heuristic signals plus a Random Forest trained on 4,000 labeled
        synthetic profiles, and it inspects the supplied activity timeline. It still cannot guarantee
        an account is fake or genuine. Live Instagram/X APIs are not used — those platforms require
        approved developer apps and prohibit scraping. See Model Lab for holdout accuracy.
      </p>
    </div>
  );
}
