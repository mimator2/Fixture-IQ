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

export default function RotationChart() {
  const { data: metrics = [], isLoading } = useCongestionMetrics();

  if (isLoading) {
    return <div className="bg-card border border-border rounded-xl p-6 animate-pulse h-96" />;
  }

  const teams = {};
  metrics.forEach((m) => {
    if (!teams[m.team_name]) teams[m.team_name] = {};
    teams[m.team_name][m.congestion_level] = m.rotation_index;
  });

  const chartData = Object.entries(teams).map(([name, levels]) => ({
    name,
    "Low": +(levels["Low"] || 0).toFixed(2),
    "Medium": +(levels["Medium"] || 0).toFixed(2),
    "High": +(levels["High"] || 0).toFixed(2),
  }));

  const allZero = chartData.every((d) => d.Low === 0 && d.Medium === 0 && d.High === 0);

  return (
    <div className="bg-card border border-border rounded-xl p-5 md:p-6">
      <h3 className="text-lg font-semibold mb-1">Squad Rotation by Team</h3>
      <p className="text-sm text-muted-foreground mb-5">
        Rotation index (0–1) under different congestion levels
      </p>
      {allZero ? (
        <div className="h-72 md:h-80 flex items-center justify-center">
          <p className="text-muted-foreground text-sm">No rotation data available for this period.</p>
        </div>
      ) : (
      <div className="h-72 md:h-80">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} barGap={2}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(215 28% 20%)" />
            <XAxis dataKey="name" tick={{ fill: "hsl(215 20% 55%)", fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: "hsl(215 20% 55%)", fontSize: 12 }} axisLine={false} tickLine={false} domain={[0, 1]} />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: 12, color: "hsl(215 20% 55%)" }} />
            <Bar dataKey="Low" fill="hsl(142 71% 45%)" radius={[4, 4, 0, 0]} />
            <Bar dataKey="Medium" fill="hsl(38 92% 50%)" radius={[4, 4, 0, 0]} />
            <Bar dataKey="High" fill="hsl(0 84% 60%)" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      )}
    </div>
  );
}
