export function RiskGauge({ value }: { value: number }) {
  const clamped = Math.max(0, Math.min(100, value));
  const color = clamped >= 71 ? "#9f2d1f" : clamped >= 45 ? "#8a5a00" : "#245c3a";

  return (
    <div className="mx-auto w-full max-w-[16rem]">
      <svg viewBox="0 0 200 120" className="w-full" role="img" aria-label={`Inauthenticity risk ${Math.round(clamped)} percent`}>
        <path d="M20 110 A80 80 0 0 1 180 110" fill="none" stroke="#e3dcd0" strokeWidth="10" />
        <path
          d="M20 110 A80 80 0 0 1 180 110"
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeDasharray={`${(clamped / 100) * 251} 251`}
          className="transition-all duration-700"
        />
      </svg>
      <div className="-mt-8 text-center">
        <p className="font-display text-5xl leading-none">{Math.round(clamped)}%</p>
        <p className="mt-2 text-[11px] uppercase tracking-[0.16em] text-muted">Inauthenticity risk</p>
      </div>
    </div>
  );
}
