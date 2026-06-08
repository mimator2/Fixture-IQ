import { AlertTriangle, Activity, Clock, UserCheck } from "lucide-react";

export default function InjuryContext({ player }) {
  const items = [
    {
      icon: AlertTriangle,
      label: "Squad Injured",
      value: player.squad_injured_count ?? "—",
      sub: "players currently out",
      color: player.squad_injured_count >= 4 ? "text-chart-5" : "text-foreground",
    },
    {
      icon: Activity,
      label: "Soft Tissue Injuries",
      value: player.squad_soft_tissue_count ?? "—",
      sub: "in squad (last 30d)",
      color: player.squad_soft_tissue_count >= 2 ? "text-chart-4" : "text-foreground",
    },
    {
      icon: Clock,
      label: "Avg Days Out",
      value: player.squad_avg_days_out != null ? `${player.squad_avg_days_out}d` : "—",
      sub: "squad average absence",
      color: "text-foreground",
    },
    {
      icon: UserCheck,
      label: "Days Since Injury",
      value: player.days_since_last_injury != null ? `${player.days_since_last_injury}d` : "—",
      sub: player.returning_from_injury ? "⚠ Returning from injury" : "since last injury",
      color: player.returning_from_injury ? "text-chart-4" : "text-foreground",
    },
  ];

  return (
    <div className="bg-card border border-border rounded-xl p-6">
      <h3 className="font-semibold mb-4">Injury Context</h3>
      <div className="grid grid-cols-2 gap-4">
        {items.map(item => (
          <div key={item.label} className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-muted flex items-center justify-center shrink-0 mt-0.5">
              <item.icon className="w-4 h-4 text-muted-foreground" />
            </div>
            <div>
              <div className="text-xs text-muted-foreground">{item.label}</div>
              <div className={`text-lg font-bold ${item.color}`}>{item.value}</div>
              <div className="text-xs text-muted-foreground">{item.sub}</div>
            </div>
          </div>
        ))}
      </div>

      {player.injury_context_score != null && (
        <div className="mt-4 pt-4 border-t border-border">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-muted-foreground">Injury Context Score</span>
            <span className="text-sm font-semibold text-chart-5">{player.injury_context_score?.toFixed(1)}</span>
          </div>
          <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
            <div className="h-full rounded-full bg-chart-5" style={{ width: `${Math.min(100, (player.injury_context_score / 10) * 100)}%` }} />
          </div>
        </div>
      )}
    </div>
  );
}