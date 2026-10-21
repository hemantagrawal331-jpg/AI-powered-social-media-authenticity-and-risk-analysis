import { useLocation } from "react-router-dom";

const titles: Record<string, string> = {
  "/": "Desk",
  "/analyze": "Analyzer",
  "/results": "Results",
  "/compare": "Compare",
  "/network": "Network",
  "/history": "History",
  "/reports": "Reports",
  "/model": "Model lab",
  "/about": "About",
};

export function TopBar() {
  const { pathname } = useLocation();
  const key = pathname.startsWith("/results") ? "/results" : pathname;
  const title = titles[key] || "FakeGuard";

  return (
    <header className="mb-8 flex items-baseline justify-between gap-4 border-b border-line pb-3">
      <p className="kicker">{title}</p>
      <p className="hidden text-[11px] text-muted sm:block">No platform login · public or supplied fields only</p>
    </header>
  );
}
