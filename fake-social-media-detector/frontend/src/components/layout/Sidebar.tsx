import { NavLink } from "react-router-dom";

const links = [
  { to: "/", label: "Desk" },
  { to: "/analyze", label: "Analyzer" },
  { to: "/results", label: "Results" },
  { to: "/compare", label: "Compare" },
  { to: "/network", label: "Network" },
  { to: "/history", label: "History" },
  { to: "/reports", label: "Reports" },
  { to: "/model", label: "Model lab" },
  { to: "/about", label: "About" },
];

export function Sidebar() {
  return (
    <aside className="sticky top-0 hidden h-screen w-[220px] shrink-0 flex-col border-r border-line bg-paper px-5 py-6 lg:flex">
      <NavLink to="/" className="block">
        <p className="font-display text-[1.65rem] leading-none tracking-tight">FakeGuard</p>
        <p className="mt-2 text-xs text-muted">Authenticity desk</p>
      </NavLink>
      <nav className="mt-10 flex flex-col" aria-label="Primary">
        {links.map(({ to, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              `border-l px-3 py-1.5 text-sm transition-colors ${
                isActive ? "border-ink text-ink" : "border-transparent text-muted hover:text-ink"
              }`
            }
          >
            {label}
          </NavLink>
        ))}
      </nav>
      <p className="mt-auto text-[11px] leading-5 text-muted">
        Ensemble v2.1. Scores use the fields you supply. Missing data lowers confidence, not risk.
      </p>
    </aside>
  );
}
