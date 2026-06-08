import { useCongestionMetrics } from "@/hooks/useCongestionMetrics";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-popover border border-border rounded-lg p-3 shadow-xl text-sm">
      <p className="font-semibold text-foreground mb-1.5">{label}</p>
      {payload.map((entry) => (
        <p key={entry.name} className="text-muted-foreground flex justify-between gap-4">
          <span>{entry.name}:</span>
          <span className="font-medium text-foreground">{entry.value}</span>
        </p>
      ))}
    </div>
  );
};

export default function CongestionChart() {
  const { data: metrics = [], isLoading } = useCongestionMetrics();

  if (isLoading) {
    return (
      <div className="bg-card border border-border rounded-xl p-6 animate-pulse h-96" />
    );
  }

  const grouped = {};
  metrics.forEach((m) => {
    if (!grouped[m.congestion_level]) {
      grouped[m.congestion_level] = { level: m.congestion_level, ppm: [], xgf: [], winRate: [] };
    }
    if (m.points_per_match != null) grouped[m.congestion_level].ppm.push(m.points_per_match);
    if (m.xg_for != null) grouped[m.congestion_level].xgf.push(m.xg_for);
    if (m.win_rate != null) grouped[m.congestion_level].winRate.push(m.win_rate);
  });

  const avg = (arr) => arr.length ? +(arr.reduce((a, b) => a + b, 0) / arr.length).toFixed(2) : 0;

  const chartData = ["Low", "Medium", "High"]
    .filter((l) => grouped[l])
    .map((l) => ({
      name: `${l} Congestion`,
      "Points/Match": avg(grouped[l].ppm),
      "xG For": avg(grouped[l].xgf),
      "Win Rate %": avg(grouped[l].winRate),
    }));

  return (
    <div className="bg-card border border-border rounded-xl p-5 md:p-6">
      <h3 className="text-lg font-semibold mb-1">Performance by Congestion Level</h3>
      <p className="text-sm text-muted-foreground mb-5">
        Average metrics across all teams grouped by fixture density
      </p>
      <div className="h-72 md:h-80">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} barGap={4}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(215 28% 20%)" />
            <XAxis dataKey="name" tick={{ fill: "hsl(215 20% 55%)", fontSize: 12 }} axisLine={false} tickLine={false} />
            <YAxis yAxisId="left" tick={{ fill: "hsl(215 20% 55%)", fontSize: 12 }} axisLine={false} tickLine={false} domain={[0, "auto"]} />
            <YAxis yAxisId="right" orientation="right" tick={{ fill: "hsl(215 20% 55%)", fontSize: 12 }} axisLine={false} tickLine={false} domain={[0, 100]} label={{ value: "Win Rate %", angle: 90, position: "insideRight", offset: -5, style: { fill: "hsl(215 20% 55%)", fontSize: 11 } }} />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: 12, color: "hsl(215 20% 55%)" }} />
            <Bar yAxisId="left" dataKey="Points/Match" fill="hsl(217 91% 60%)" radius={[4, 4, 0, 0]} />
            <Bar yAxisId="left" dataKey="xG For" fill="hsl(187 72% 50%)" radius={[4, 4, 0, 0]} />
            <Bar yAxisId="right" dataKey="Win Rate %" fill="hsl(142 71% 45%)" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
