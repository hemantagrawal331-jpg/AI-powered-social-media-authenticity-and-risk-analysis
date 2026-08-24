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
        <h1 className="font-display text-3xl">Network & clusters</h1>
        <p className="mt-1 text-sm text-slate-400">
          Prototype social graph generated from bundled samples — not live Instagram/X data.
        </p>
      </div>
      <ErrorBanner message={error} />
      <GlassCard title="Local sample neighborhood">
        <svg viewBox="0 0 720 360" className="h-[360px] w-full">
          {(data?.edges || []).map((edge) => {
            const a = layout[edge.source];
            const b = layout[edge.target];
            if (!a || !b) return null;
            return <line key={`${edge.source}-${edge.target}`} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="rgba(62,224,197,0.28)" />;
          })}
          {(data?.nodes || []).map((node) => {
            const point = layout[node.id];
            if (!point) return null;
            const color = node.risk >= 70 ? "#ff4d6d" : node.risk >= 45 ? "#f5c14a" : "#3ee0c5";
            return (
              <g key={node.id}>
                <circle cx={point.x} cy={point.y} r={18} fill={color} fillOpacity={0.9} />
                <text x={point.x} y={point.y + 32} textAnchor="middle" fill="#cbd5e1" fontSize="11">
                  {node.label}
                </text>
              </g>
            );
          })}
        </svg>
        <p className="mt-2 text-xs text-slate-500">{data?.prototype_note}</p>
      </GlassCard>
      {(data?.clusters || []).map((cluster) => (
        <GlassCard key={cluster.title} title="Bot / suspicious cluster detection">
          <div className="flex flex-wrap items-center gap-3">
            <p className="font-display text-xl">{cluster.title}</p>
            <RiskBadge level={`${cluster.risk}% risk`} />
          </div>
          <p className="mt-2 text-sm text-slate-300">Cluster size: {cluster.size}</p>
          <p className="mt-2 text-sm text-slate-400">{cluster.explanation}</p>
          <p className="mt-3 text-sm text-slate-300">Members: {cluster.members.map((item) => `@${item}`).join(", ")}</p>
        </GlassCard>
      ))}
    </div>
  );
}

function positionNodes(nodes: { id: string }[]) {
  const map: Record<string, { x: number; y: number }> = {};
  const cx = 360;
  const cy = 170;
  const radius = 120;
  nodes.forEach((node, index) => {
    const angle = (index / Math.max(nodes.length, 1)) * Math.PI * 2;
    map[node.id] = { x: cx + radius * Math.cos(angle), y: cy + radius * Math.sin(angle) };
  });
  return map;
}
