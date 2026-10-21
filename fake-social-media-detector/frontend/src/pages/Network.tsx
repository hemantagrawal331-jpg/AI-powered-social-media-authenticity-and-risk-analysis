import { useEffect, useMemo, useState } from "react";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { GlassCard } from "../components/common/GlassCard";
import { RiskBadge } from "../components/common/RiskBadge";
import { api } from "../services/api";

interface Overview {
  title?: string;
  prototype_note?: string;
  nodes?: { id: string; label: string; group: string; risk: number }[];
  edges?: { source: string; target: string; relation: string }[];
  clusters?: { title: string; size: number; risk: number; explanation: string; members: string[] }[];
}

export function Network() {
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .networkOverview()
      .then((payload) => setData(payload as Overview))
      .catch((err: Error) => setError(err.message));
  }, []);

  const layout = useMemo(() => positionNodes(data?.nodes || []), [data]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-4xl tracking-tight">Network</h1>
        <p className="mt-2 max-w-prose text-sm text-muted">
          A graph of the bundled samples. It is not a live map of Instagram or X.
        </p>
      </div>
      <ErrorBanner message={error} />
      <GlassCard title="Local sample neighborhood">
        <svg viewBox="0 0 860 440" className="h-auto w-full" role="img" aria-label="Bundled sample accounts arranged in a circle">
          {(data?.edges || []).map((edge) => {
            const a = layout[edge.source];
            const b = layout[edge.target];
            if (!a || !b) return null;
            return <line key={`${edge.source}-${edge.target}`} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="#d9d1c4" />;
          })}
          {(data?.nodes || []).map((node) => {
            const point = layout[node.id];
            if (!point) return null;
            const color = node.risk >= 70 ? "#9f2d1f" : node.risk >= 45 ? "#8a5a00" : "#245c3a";
            return (
              <g key={node.id}>
                <circle cx={point.x} cy={point.y} r={16} fill={color} stroke="#fbf9f5" strokeWidth="2" />
                <text x={point.lx} y={point.ly} textAnchor={point.anchor} fill="#3f3a36" fontSize="11">
                  {node.label}
                </text>
              </g>
            );
          })}
        </svg>
        <p className="mt-2 text-xs text-muted">{data?.prototype_note}</p>
      </GlassCard>
      {(data?.clusters || []).map((cluster) => (
        <GlassCard key={cluster.title} title="Bot / suspicious cluster detection">
          <div className="flex flex-wrap items-center gap-3">
            <p className="font-display text-xl">{cluster.title}</p>
            <RiskBadge level={`${cluster.risk}% risk`} />
          </div>
          <p className="mt-2 text-sm text-ink-soft">Cluster size: {cluster.size}</p>
          <p className="mt-2 text-sm text-muted">{cluster.explanation}</p>
          <p className="mt-3 text-sm text-ink-soft">Members: {cluster.members.map((item) => `@${item}`).join(", ")}</p>
        </GlassCard>
      ))}
    </div>
  );
}

function positionNodes(nodes: { id: string }[]) {
  const map: Record<string, { x: number; y: number; lx: number; ly: number; anchor: "start" | "middle" | "end" }> = {};
  const cx = 430;
  const cy = 210;
  const rx = 250;
  const ry = 145;
  nodes.forEach((node, index) => {
    const angle = (index / Math.max(nodes.length, 1)) * Math.PI * 2 - Math.PI / 2;
    const x = cx + rx * Math.cos(angle);
    const y = cy + ry * Math.sin(angle);
    const cos = Math.cos(angle);
    const sin = Math.sin(angle);
    const anchor = cos > 0.35 ? "start" : cos < -0.35 ? "end" : "middle";
    map[node.id] = {
      x,
      y,
      lx: x + (anchor === "start" ? 18 : anchor === "end" ? -18 : 0),
      ly: y + (sin >= 0.35 ? 28 : sin <= -0.35 ? -16 : 4),
      anchor,
    };
  });
  return map;
}
