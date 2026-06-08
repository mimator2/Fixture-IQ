import { RadarChart, Radar, PolarGrid, PolarAngleAxis, Tooltip, ResponsiveContainer } from "recharts";

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-card border border-border rounded-lg p-3 text-xs shadow-lg">
      <p className="font-semibold">{payload[0]?.payload?.metric}</p>
      <p className="text-primary">Value: {payload[0]?.value?.toFixed(1)}</p>
    </div>
  );
};

export default function ActionLoadBreakdown({ player }) {
  const data = [
    { metric: "Shots",         value: player.shots_last_5 ?? 0 },
    { metric: "Key Passes",    value: player.key_passes_last_5 ?? 0 },
    { metric: "Tackles",       value: player.tackles_last_5 ?? 0 },
    { metric: "Interceptions", value: player.interceptions_last_5 ?? 0 },
    { metric: "Dribbles",      value: player.dribbles_last_5 ?? 0 },
    { metric: "Duels",         value: (player.duels_last_5 ?? 0) / 3 }, // scaled
  ];

  return (
    <div className="bg-card border border-border rounded-xl p-6">
      <h3 className="font-semibold mb-1">Action Load (Last 5 Matches)</h3>
      <p className="text-xs text-muted-foreground mb-4">High action load contributes to fatigue independent of minutes played.</p>
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={data}>
            <PolarGrid stroke="hsl(var(--border))" />
            <PolarAngleAxis dataKey="metric" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} />
            <Radar name="Load" dataKey="value" stroke="hsl(var(--accent))" fill="hsl(var(--accent))" fillOpacity={0.25} strokeWidth={2} />
            <Tooltip content={<CustomTooltip />} />
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}