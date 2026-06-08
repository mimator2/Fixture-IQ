import { usePlayerRisks } from "@/hooks/usePlayerRisks";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { riskConfig } from "./RiskBadge";
import { AlertTriangle, Users } from "lucide-react";

const BANDS = ["Low", "Medium", "High", "Very High"];
const COLORS = ["#22c55e", "#f59e0b", "#ef4444", "#dc2626"];

export default function TeamRiskSummary({ teamFilter }) {
  const { data: players = [], isLoading, error } = usePlayerRisks();

  const filtered = teamFilter ? players.filter(p => p.team_name === teamFilter) : players;

  const counts = BANDS.map(band => ({
    name: band,
    value: filtered.filter(p => p.risk_band === band).length,
  }));

  const highRisk = filtered.filter(p => p.risk_band === "High" || p.risk_band === "Very High");

  if (isLoading) return <div className="bg-card border border-border rounded-xl p-6 animate-pulse h-64" />;
  if (error) return (
    <div className="bg-card border border-destructive/50 rounded-xl p-6 text-center">
      <p className="text-destructive font-semibold text-sm">Failed to load player data</p>
      <p className="text-muted-foreground text-xs mt-1">{error.message}</p>
    </div>
  );

  return (
    <div className="bg-card border border-border rounded-xl p-6">
      <div className="flex items-center gap-2 mb-4">
        <Users className="w-4 h-4 text-primary" />
        <h3 className="font-semibold">Squad Risk Distribution</h3>
        {teamFilter && <span className="text-xs text-muted-foreground">— {teamFilter}</span>}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={counts} cx="50%" cy="50%" innerRadius={50} outerRadius={80} dataKey="value" paddingAngle={3}>
                {counts.map((_, i) => <Cell key={i} fill={COLORS[i]} />)}
              </Pie>
              <Tooltip
                contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8 }}
                labelStyle={{ color: "hsl(var(--foreground))" }}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="space-y-2">
          {BANDS.map((band, i) => {
            const cfg = riskConfig[band];
            const count = counts[i].value;
            const pct = filtered.length > 0 ? Math.round((count / filtered.length) * 100) : 0;
            return (
              <div key={band} className="flex items-center gap-3">
                <span className={`w-2 h-2 rounded-full ${cfg.dot}`} />
                <span className="text-sm flex-1">{band}</span>
                <div className="flex items-center gap-2">
                  <div className="w-24 h-1.5 bg-muted rounded-full overflow-hidden">
                    <div className="h-full rounded-full" style={{ width: `${pct}%`, background: COLORS[i] }} />
                  </div>
                  <span className="text-xs text-muted-foreground w-8 text-right">{count}</span>
                </div>
              </div>
            );
          })}

          {highRisk.length > 0 && (
            <div className="mt-4 pt-4 border-t border-border">
              <div className="flex items-center gap-1.5 text-chart-5 text-xs font-semibold mb-2">
                <AlertTriangle className="w-3.5 h-3.5" />
                Requires Attention
              </div>
              {highRisk.slice(0, 4).map(p => (
                <div key={p.id} className="text-xs text-muted-foreground">{p.player_name} — {p.team_name}</div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
