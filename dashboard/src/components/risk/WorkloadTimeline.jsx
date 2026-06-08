import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-card border border-border rounded-lg p-3 text-xs shadow-lg">
      <p className="font-semibold mb-1">{label}</p>
      {payload.map(p => (
        <p key={p.dataKey} style={{ color: p.color }}>{p.name}: {p.value}</p>
      ))}
    </div>
  );
};

export default function WorkloadTimeline({ data = [] }) {
  if (!data.length) return (
    <div className="bg-card border border-border rounded-xl p-6 text-center text-muted-foreground text-sm">
      No timeline data available.
    </div>
  );

  return (
    <div className="bg-card border border-border rounded-xl p-6">
      <h3 className="font-semibold mb-4">Workload Timeline (Last 8 Weeks)</h3>
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis dataKey="week" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} />
            <YAxis tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Area type="monotone" dataKey="minutes" name="Minutes" stroke="hsl(var(--primary))" fill="hsl(var(--primary)/.15)" strokeWidth={2} />
            <Area type="monotone" dataKey="fatigue_score" name="Fatigue Score" stroke="hsl(var(--chart-5))" fill="hsl(var(--chart-5)/.10)" strokeWidth={2} />
            <Area type="monotone" dataKey="rest_days" name="Rest Days" stroke="hsl(var(--accent))" fill="hsl(var(--accent)/.10)" strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}