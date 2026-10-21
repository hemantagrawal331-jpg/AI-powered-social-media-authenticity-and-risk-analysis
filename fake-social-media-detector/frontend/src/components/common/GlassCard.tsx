import type { ReactNode } from "react";

export function GlassCard({
  children,
  className = "",
  title,
  action,
}: {
  children: ReactNode;
  className?: string;
  title?: string;
  action?: ReactNode;
}) {
  return (
    <section className={`border border-line bg-paper-raised p-5 sm:p-6 ${className}`}>
      {(title || action) && (
        <div className="mb-4 flex items-baseline justify-between gap-3 border-b border-line pb-3">
          {title ? <h2 className="font-display text-xl tracking-tight">{title}</h2> : <span />}
          {action}
        </div>
      )}
      {children}
    </section>
  );
}
