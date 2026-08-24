export function riskTone(level: string) {
  const value = level.toLowerCase();
  if (value.includes("very high") || value === "high") return "bg-rose-500/15 text-rose-300 border-rose-400/30";
  if (value.includes("suspicious") || value.includes("moderate")) return "bg-orange-500/15 text-orange-200 border-orange-400/30";
  if (value.includes("low")) return "bg-amber-400/15 text-amber-200 border-amber-300/30";
  if (value.includes("genuine") || value.includes("minimal")) return "bg-emerald-400/15 text-emerald-200 border-emerald-300/30";
  return "bg-slate-500/15 text-slate-200 border-white/10";
}

export function RiskBadge({ level }: { level: string }) {
  return (
    <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-medium ${riskTone(level)}`}>
      {level}
    </span>
  );
}
