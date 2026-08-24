export function RiskGauge({ value }: { value: number }) {
  const clamped = Math.max(0, Math.min(100, value));
  const angle = (clamped / 100) * 180;
  const color = clamped >= 71 ? "#ff4d6d" : clamped >= 51 ? "#f5c14a" : "#3ee0c5";

  return (
    <div className="relative mx-auto w-64">
      <svg viewBox="0 0 200 120" className="w-full">
        <path d="M20 110 A80 80 0 0 1 180 110" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="16" strokeLinecap="round" />
        <path
          d="M20 110 A80 80 0 0 1 180 110"
          fill="none"
          stroke={color}
          strokeWidth="16"
          strokeLinecap="round"
          strokeDasharray={`${(clamped / 100) * 251} 251`}
          className="transition-all duration-700"
        />
        <line
          x1="100"
          y1="110"
          x2={100 + 62 * Math.cos(((180 - angle) * Math.PI) / 180)}
          y2={110 - 62 * Math.sin(((180 - angle) * Math.PI) / 180)}
          stroke="white"
          strokeWidth="3"
          strokeLinecap="round"
        />
      </svg>
      <div className="absolute inset-x-0 bottom-1 text-center">
        <p className="font-display text-4xl font-bold">{Math.round(clamped)}%</p>
        <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Fake probability</p>
      </div>
    </div>
  );
}
