import { usePlayerRisks } from "@/hooks/usePlayerRisks";
import PlayerRiskTable from "@/components/risk/PlayerRiskTable";
import TeamRiskSummary from "@/components/risk/TeamRiskSummary";
import { Activity, AlertTriangle, Users, ShieldCheck } from "lucide-react";

export default function PlayerMonitor() {
  const { data: players = [] } = usePlayerRisks();

  const stats = [
    {
      label: "Total Monitored",
      value: players.length,
      icon: Users,
      color: "text-primary",
      bg: "bg-primary/10",
    },
    {
      label: "High / Very High",
      value: players.filter(p => p.risk_band === "High" || p.risk_band === "Very High").length,
      icon: AlertTriangle,
      color: "text-chart-5",
      bg: "bg-chart-5/10",
    },
    {
      label: "Medium Risk",
      value: players.filter(p => p.risk_band === "Medium").length,
      icon: Activity,
      color: "text-chart-4",
      bg: "bg-chart-4/10",
    },
    {
      label: "Low Risk",
      value: players.filter(p => p.risk_band === "Low").length,
      icon: ShieldCheck,
      color: "text-chart-3",
      bg: "bg-chart-3/10",
    },
  ];

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-7xl mx-auto px-4 py-8 space-y-8">

        {/* Header */}
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Activity className="w-5 h-5 text-primary" />
            <h1 className="text-2xl font-bold">Player Risk Monitor</h1>
          </div>
          <p className="text-muted-foreground text-sm max-w-2xl">
            CatBoost V6 dual-score system — Workload/Fatigue Score (V6 No Rating Baseline) + Performance Risk Score (V6 Full).
            Players are flagged for monitoring, not diagnosed with fatigue.
          </p>
        </div>

        {/* Stats Bar */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {stats.map(s => (
            <div key={s.label} className="bg-card border border-border rounded-xl p-4 flex items-center gap-3">
              <div className={`w-9 h-9 rounded-lg ${s.bg} flex items-center justify-center shrink-0`}>
                <s.icon className={`w-4 h-4 ${s.color}`} />
              </div>
              <div>
                <div className={`text-xl font-bold ${s.color}`}>{s.value}</div>
                <div className="text-xs text-muted-foreground">{s.label}</div>
              </div>
            </div>
          ))}
        </div>

        {/* Team Risk Summary */}
        <TeamRiskSummary />

        {/* Player Table */}
        <div>
          <h2 className="text-lg font-semibold mb-4">Player Risk List</h2>
          <PlayerRiskTable />
        </div>

      </div>
    </div>
  );
}
