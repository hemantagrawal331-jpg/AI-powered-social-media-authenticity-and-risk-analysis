import type { ReactNode } from "react";
import { Disclaimer } from "./Disclaimer";
import { MobileNav } from "./MobileNav";
import { Sidebar } from "./Sidebar";

export function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="relative min-h-screen lg:pl-72">
      <Sidebar />
      <div className="px-4 py-6 sm:px-8">
        <MobileNav />
        <Disclaimer />
        {children}
      </div>
    </div>
  );
}
