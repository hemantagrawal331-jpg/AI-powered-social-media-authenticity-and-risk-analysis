import {
  GitCompare,
  History,
  Home,
  Info,
  Network,
  ScanSearch,
  FileText,
  Shield,
} from "lucide-react";
import { NavLink } from "react-router-dom";

const links = [
  { to: "/", label: "Home", icon: Home },
  { to: "/analyze", label: "Analyzer", icon: ScanSearch },
  { to: "/results", label: "Results", icon: Shield },
  { to: "/compare", label: "Compare", icon: GitCompare },
  { to: "/network", label: "Network", icon: Network },
  { to: "/history", label: "History", icon: History },
  { to: "/reports", label: "Reports", icon: FileText },
  { to: "/about", label: "About", icon: Info },
];

export function Sidebar() {
  return (
    <aside className="glass fixed inset-y-0 left-0 z-30 hidden w-72 flex-col p-5 lg:flex">
      <div className="mb-8 flex items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-accent/15 text-accent shadow-glow">
          <Shield className="h-6 w-6" />
        </div>
        <div>
          <p className="font-display text-lg font-semibold tracking-tight">FakeGuard AI</p>
          <p className="text-xs text-slate-400">Authenticity & risk analysis</p>
        </div>
      </div>
      <nav className="space-y-1">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition ${
                isActive
                  ? "bg-accent/15 text-accent"
                  : "text-slate-300 hover:bg-white/5 hover:text-white"
              }`
            }
          >
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        ))}
      </nav>
      <p className="mt-auto text-[11px] leading-5 text-slate-500">
        Prototype heuristic engine. No social-media logins. No live scraping.
      </p>
    </aside>
  );
}
