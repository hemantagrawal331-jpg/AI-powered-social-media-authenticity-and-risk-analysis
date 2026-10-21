import type { ReactNode } from "react";
import {
  Bar,
  BarChart,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useMotion } from "../../hooks/useMotion";
import type { AnalysisResult } from "../../types/analysis";

const tooltipStyle = {
  background: "#fbf9f5",
  border: "1px solid #e3dcd0",
  borderRadius: 0,
  color: "#1c1917",
  fontSize: 12,
};

const tick = { fill: "#6f6860", fontSize: 11 };

export function DashboardCharts({ result }: { result: AnalysisResult }) {
  const motion = useMotion();
  const domainRadar = Object.entries(result.domain_scores || {}).map(([name, card]) => ({
    label: name.replaceAll("_", " "),
    value: card.score,
  }));
  const donut = [
    { name: "Combined risk score", value: result.fake_probability },
    { name: "Residual", value: Math.max(0, 100 - result.fake_probability) },
  ];
  const bars = result.score_contributions.map((item) => ({
    name: item.feature.replace(" Risk", "").replace(" Anomaly", "").replace(" Patterns", "").replace(" Signal", ""),
    value: item.raw_score,
  }));

  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <ChartCard title="Domain authenticity">
        <p className="mb-2 text-xs text-muted">Higher means the domain looks more consistent with a genuine account.</p>
        <ResponsiveContainer width="100%" height={280}>
          <RadarChart data={domainRadar.length ? domainRadar : result.radar}>
            <PolarGrid stroke="#e3dcd0" />
            <PolarAngleAxis dataKey="label" tick={tick} />
            <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
            <Radar dataKey="value" stroke="#1c1917" fill="#1c1917" fillOpacity={0.12} isAnimationActive={motion} />
          </RadarChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard title="Risk and residual">
        <ResponsiveContainer width="100%" height={280}>
          <PieChart>
            <Pie data={donut} dataKey="value" innerRadius={68} outerRadius={96} paddingAngle={2} isAnimationActive={motion}>
              <Cell fill="#9f2d1f" />
              <Cell fill="#245c3a" />
            </Pie>
            <Legend />
            <Tooltip contentStyle={tooltipStyle} />
          </PieChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard title="Contribution by feature">
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={bars}>
            <XAxis dataKey="name" tick={tick} interval={0} angle={-18} textAnchor="end" height={64} />
            <YAxis domain={[0, 100]} tick={tick} />
            <Tooltip contentStyle={tooltipStyle} />
            <Bar dataKey="value" fill="#1c1917" isAnimationActive={motion} />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard title="Followers, likes, comments">
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={result.engagement_series}>
            <XAxis dataKey="date" tick={tick} />
            <YAxis tick={tick} />
            <Tooltip contentStyle={tooltipStyle} />
            <Line type="monotone" dataKey="followers" stroke="#a39c93" dot={false} isAnimationActive={motion} />
            <Line type="monotone" dataKey="likes" stroke="#1c1917" dot={false} isAnimationActive={motion} />
            <Line type="monotone" dataKey="comments" stroke="#8a5a00" dot={false} isAnimationActive={motion} />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>
    </div>
  );
}

function ChartCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="border border-line bg-paper-raised p-5">
      <h2 className="mb-3 font-display text-xl tracking-tight">{title}</h2>
      {children}
    </section>
  );
}
