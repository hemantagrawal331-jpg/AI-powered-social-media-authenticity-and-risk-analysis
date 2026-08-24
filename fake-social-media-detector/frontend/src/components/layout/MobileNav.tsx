import { Menu, Shield, X } from "lucide-react";
import { useState } from "react";
import { NavLink } from "react-router-dom";

const links = [
  ["/", "Home"],
  ["/analyze", "Analyzer"],
  ["/results", "Results"],
  ["/compare", "Compare"],
  ["/network", "Network"],
  ["/history", "History"],
  ["/reports", "Reports"],
  ["/about", "About"],
] as const;

export function MobileNav() {
  const [open, setOpen] = useState(false);
  return (
    <div className="mb-4 flex items-center justify-between lg:hidden">
      <div className="flex items-center gap-2">
        <Shield className="h-5 w-5 text-accent" />
        <span className="font-display font-semibold">FakeGuard AI</span>
      </div>
      <button type="button" onClick={() => setOpen((v) => !v)} className="rounded-xl border border-white/10 p-2">
        {open ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
      </button>
      {open && (
        <div className="glass absolute left-4 right-4 top-16 z-40 grid gap-1 rounded-2xl p-3">
          {links.map(([to, label]) => (
            <NavLink key={to} to={to} onClick={() => setOpen(false)} className="rounded-xl px-3 py-2 text-sm hover:bg-white/5">
              {label}
            </NavLink>
          ))}
        </div>
      )}
    </div>
  );
}
