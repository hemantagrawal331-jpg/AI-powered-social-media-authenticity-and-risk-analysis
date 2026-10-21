import type { ReactNode } from "react";
import { Disclaimer } from "./Disclaimer";
import { MobileNav } from "./MobileNav";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

export function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen lg:flex">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:bg-ink focus:px-3 focus:py-2 focus:text-paper-raised"
      >
        Skip to content
      </a>
      <Sidebar />
      <div className="min-w-0 flex-1">
        <div className="mx-auto max-w-6xl px-5 py-5 sm:px-8 sm:py-8">
          <MobileNav />
          <TopBar />
          <main id="main" className="rise">
            {children}
          </main>
          <Disclaimer />
        </div>
      </div>
    </div>
  );
}
