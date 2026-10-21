import { Menu, X } from "lucide-react";
import { useState } from "react";
import { NavLink } from "react-router-dom";

const links = [
  ["/", "Desk"],
  ["/analyze", "Analyzer"],
  ["/results", "Results"],
  ["/compare", "Compare"],
  ["/network", "Network"],
  ["/history", "History"],
  ["/reports", "Reports"],
  ["/model", "Model lab"],
  ["/dataset", "Dataset"],
  ["/about", "About"],
] as const;

export function MobileNav() {
  const [open, setOpen] = useState(false);
  return (
    <div className="mb-6 border-b border-line pb-3 lg:hidden">
      <div className="flex items-center justify-between">
        <NavLink to="/" className="font-display text-2xl leading-none">
          FakeGuard
        </NavLink>
        <button
          type="button"
          aria-expanded={open}
          aria-controls="mobile-nav"
          onClick={() => setOpen((value) => !value)}
          className="border border-line p-2"
        >
          {open ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          <span className="sr-only">{open ? "Close menu" : "Open menu"}</span>
        </button>
      </div>
      {open && (
        <nav id="mobile-nav" className="mt-3 grid border-t border-line pt-2" aria-label="Primary">
          {links.map(([to, label]) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                `py-2 text-sm ${isActive ? "text-ink" : "text-muted"}`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
      )}
    </div>
  );
}
