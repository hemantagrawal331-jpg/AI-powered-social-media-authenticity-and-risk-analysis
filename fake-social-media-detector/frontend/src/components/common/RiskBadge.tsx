export function riskTone(level: string) {
  const value = level.toLowerCase();
  if (value.includes("inauthentic") || value.includes("very high") || value.includes("high"))
    return "border-signal/30 bg-signal/5 text-signal";
  if (value.includes("suspicious") || value.includes("moderate"))
    return "border-caution/30 bg-caution/5 text-caution";
  if (value.includes("mostly") || value.includes("low"))
    return "border-caution/30 bg-caution/5 text-caution";
  if (value.includes("genuine") || value.includes("minimal"))
    return "border-verified/30 bg-verified/5 text-verified";
  return "border-line bg-paper text-muted";
}

export function RiskBadge({ level }: { level: string }) {
  return (
    <span className={`inline-flex border px-1.5 py-0.5 text-[11px] font-medium uppercase tracking-[0.12em] ${riskTone(level)}`}>
      {level}
    </span>
  );
}
