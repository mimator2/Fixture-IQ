import { useTeams } from "@/hooks/useTeams";
import { usePlayerRisks } from "@/hooks/usePlayerRisks";
import { useCongestionMetrics } from "@/hooks/useCongestionMetrics";
import { Users, Calendar, TrendingDown, Shield } from "lucide-react";

export default function StatsOverview() {
  const { data: teams = [] } = useTeams();
  const { data: players = [] } = usePlayerRisks();
  const { data: metrics = [] } = useCongestionMetrics();

  const totalMatches = metrics.reduce((sum, m) => sum + (m.matches || 0), 0);

  const lowRest = metrics
    .filter(m => m.congestion_level === "Low")
    .reduce((sum, m, _, arr) => sum + (m.avg_rest_days || 0), 0);
  const lowCount = metrics.filter(m => m.congestion_level === "Low").length;
  const avgLowRest = lowCount > 0 ? lowRest / lowCount : 0;

  const mediumRest = metrics
    .filter(m => m.congestion_level === "Medium")
    .reduce((sum, m, _, arr) => sum + (m.avg_rest_days || 0), 0);
  const mediumCount = metrics.filter(m => m.congestion_level === "Medium").length;
  const avgMediumRest = mediumCount > 0 ? mediumRest / mediumCount : 0;

  const restDrop = avgLowRest - avgMediumRest;

  const stats = [
    {
      label: "Teams Analysed",
      value: teams.length,
      sub: "Premier League clubs in Europe",
      icon: Users,
      color: "text-primary",
      bg: "bg-primary/10",
    },
    {
      label: "Players Monitored",
      value: players.length,
      sub: "XGBoost V4B risk score",
      icon: Shield,
      color: "text-accent",
      bg: "bg-accent/10",
    },
    {
      label: "Matches Tracked",
      value: `${totalMatches}+`,
      sub: "Across all competitions",
      icon: Calendar,
      color: "text-chart-5",
      bg: "bg-destructive/10",
    },
    {
      label: "Rest Drop",
      value: `${avgMediumRest.toFixed(1) - avgLowRest.toFixed(1)}d`,
      sub: "Avg rest: Low vs Medium congestion \n | (≥7d) vs (4-6d)",
      icon: TrendingDown,
      color: "text-chart-3",
      bg: "bg-chart-3/10",
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      {stats.map((stat) => {
        const Icon = stat.icon;
        return (
          <div key={stat.label} className="bg-card border border-border rounded-xl p-4 md:p-5 hover:border-primary/30 transition-colors">
            <div className={`w-9 h-9 rounded-lg ${stat.bg} flex items-center justify-center mb-3`}>
              <Icon className={`w-4 h-4 ${stat.color}`} />
            </div>
            <div className="text-2xl md:text-3xl font-bold tracking-tight mb-0.5">{stat.value}</div>
            <div className="text-sm font-medium text-foreground/80">{stat.label}</div>
            <div className="text-xs text-muted-foreground mt-0.5 whitespace-pre-line">{stat.sub}</div>

          </div>
        );
      })}
    </div>
  );
}
