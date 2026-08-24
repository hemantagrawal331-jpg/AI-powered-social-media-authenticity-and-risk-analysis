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
    <section className={`glass rounded-3xl p-5 ${className}`}>
      {(title || action) && (
        <div className="mb-4 flex items-center justify-between gap-3">
          {title ? <h3 className="font-display text-base font-semibold">{title}</h3> : <span />}
          {action}
        </div>
      )}
      {children}
    </section>
  );
}
