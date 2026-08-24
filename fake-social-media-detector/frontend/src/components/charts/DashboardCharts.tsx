import type { ReactNode } from "react";
import {
  Cell,
  Legend,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  PieChart,
  Pie,
  LineChart,
  Line,
} from "recharts";
import type { AnalysisResult } from "../../types/analysis";

const tooltipStyle = {
  background: "#111a2e",
  border: "1px solid rgba(255,255,255,0.08)",
  borderRadius: 12,
};

export function DashboardCharts({ result }: { result: AnalysisResult }) {
  const donut = [
    { name: "Fake risk", value: result.fake_probability },
    { name: "Residual genuine", value: Math.max(0, 100 - result.fake_probability) },
  ];
  const bars = result.score_contributions.map((item) => ({
    name: item.feature.replace(" Risk", "").replace(" Anomaly", "").replace(" Patterns", "").replace(" Signal", ""),
    value: item.raw_score,
  }));

  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <ChartCard title="Risk radar">
        <ResponsiveContainer width="100%" height={280}>
          <RadarChart data={result.radar}>
            <PolarGrid stroke="rgba(255,255,255,0.08)" />
            <PolarAngleAxis dataKey="label" tick={{ fill: "#94a3b8", fontSize: 11 }} />
            <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
            <Radar dataKey="value" stroke="#3ee0c5" fill="#3ee0c5" fillOpacity={0.28} />
          </RadarChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard title="Fake vs residual genuine">
        <ResponsiveContainer width="100%" height={280}>
          <PieChart>
            <Pie data={donut} dataKey="value" innerRadius={68} outerRadius={96} paddingAngle={3}>
              <Cell fill="#ff4d6d" />
              <Cell fill="#3ee0c5" />
            </Pie>
            <Legend />
            <Tooltip contentStyle={tooltipStyle} />
          </PieChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard title="Risk contribution by feature">
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={bars}>
            <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 10 }} interval={0} angle={-18} textAnchor="end" height={60} />
            <YAxis domain={[0, 100]} tick={{ fill: "#94a3b8", fontSize: 11 }} />
            <Tooltip contentStyle={tooltipStyle} />
            <Bar dataKey="value" fill="#4f8cff" radius={[8, 8, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard title="Followers vs likes / comments">
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={result.engagement_series}>
            <XAxis dataKey="date" tick={{ fill: "#94a3b8", fontSize: 10 }} />
            <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
            <Tooltip contentStyle={tooltipStyle} />
            <Line type="monotone" dataKey="followers" stroke="#94a3b8" dot={false} />
            <Line type="monotone" dataKey="likes" stroke="#3ee0c5" dot={false} />
            <Line type="monotone" dataKey="comments" stroke="#f5c14a" dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>
    </div>
  );
}

function ChartCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="glass rounded-3xl p-5">
      <h3 className="mb-3 font-display text-sm font-semibold">{title}</h3>
      {children}
    </div>
  );
}
