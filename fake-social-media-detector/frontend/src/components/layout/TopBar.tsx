export function TopBar() {
  return (
    <header className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-white/5 bg-ink-900/70 px-4 py-3 backdrop-blur">
      <div>
        <p className="font-display text-sm font-semibold tracking-wide">FAKEGUARD AI</p>
        <p className="text-[11px] uppercase tracking-[0.22em] text-slate-500">Social media authenticity intelligence</p>
      </div>
      <div className="flex items-center gap-2 rounded-full border border-emerald-400/20 bg-emerald-400/10 px-3 py-1 text-[11px] text-emerald-200">
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
        SYSTEM STATUS · LIVE · v2.1.0
      </div>
    </header>
  );
}