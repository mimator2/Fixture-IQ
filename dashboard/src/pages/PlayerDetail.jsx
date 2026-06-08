import { useParams, Link } from "react-router-dom";
import { usePlayerRisk } from "@/hooks/usePlayerRisks";
import RiskBadge from "@/components/risk/RiskBadge";
import FlagBadge from "@/components/risk/FlagBadge";
import ScoreGauge from "@/components/risk/ScoreGauge";
import WorkloadTimeline from "@/components/risk/WorkloadTimeline";
import ActionLoadBreakdown from "@/components/risk/ActionLoadBreakdown";
import InjuryContext from "@/components/risk/InjuryContext";
import { ArrowLeft, Shield, Calendar, RotateCcw, Zap } from "lucide-react";

const ACTION_COLORS = {
  "Normal Monitoring":              "bg-chart-3/10 text-chart-3 border-chart-3/20",
  "Monitor Training Response":      "bg-chart-4/10 text-chart-4 border-chart-4/20",
  "Check GPS/Wellness/Soreness":    "bg-chart-4/10 text-chart-4 border-chart-4/20",
  "Review Minutes Plan":            "bg-chart-5/10 text-chart-5 border-chart-5/20",
  "Consider Rest / Recovery Protocol": "bg-red-400/10 text-red-400 border-red-400/20",
};

export default function PlayerDetail() {
  const { playerId } = useParams();
  const { data: player, isLoading } = usePlayerRisk(playerId);

  if (isLoading) return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-4">
      {[1,2,3].map(i => <div key={i} className="bg-card border border-border rounded-xl h-40 animate-pulse" />)}
    </div>
  );

  if (!player) return (
    <div className="max-w-5xl mx-auto px-4 py-12 text-center text-muted-foreground">Player not found.</div>
  );

  const minuteStats = [
    { label: "Last 7d",  value: player.minutes_last_7,  icon: Calendar },
    { label: "Last 14d", value: player.minutes_last_14, icon: Calendar },
    { label: "Last 21d", value: player.minutes_last_21, icon: Calendar },
    { label: "Last 28d", value: player.minutes_last_28, icon: Calendar },
    { label: "Starts (5)", value: player.starts_last_5, icon: RotateCcw },
    { label: "Full 90s (5)", value: player.full_90s_last_5, icon: Zap },
    { label: "Avg Rest Days", value: player.avg_rest_days_last_5 != null ? `${player.avg_rest_days_last_5}d` : "—", icon: Calendar },
    { label: "UCL Min (21d)", value: player.ucl_minutes_last_21, icon: Shield },
  ];

  const actionCls = ACTION_COLORS[player.recommended_action] || "bg-muted text-muted-foreground border-border";

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">

        {/* Back */}
        <Link to="/player-monitor" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back to Monitor
        </Link>

        {/* Header */}
        <div className="bg-card border border-border rounded-xl p-6">
          <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold mb-1">{player.player_name}</h1>
              <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground mb-3">
                <span>{player.team_name}</span>
                <span>·</span>
                <span>{player.position}</span>
                <span>·</span>
                <span>{player.player_role}</span>
                <span>·</span>
                <span>{player.season}</span>
              </div>
              <div className="flex flex-wrap gap-2 items-center">
                <RiskBadge band={player.risk_band} size="lg" />
                {(player.risk_flags || []).map(f => <FlagBadge key={f} flag={f} />)}
              </div>
            </div>
            <div className={`px-4 py-2 rounded-lg border text-sm font-medium ${actionCls} text-center max-w-56`}>
              {player.recommended_action}
            </div>
          </div>
        </div>

        {/* Dual Scores */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <ScoreGauge
            label="Workload / Fatigue Score"
            description="V6 No Rating Baseline — coach-facing"
            score={player.fatigue_score}
            color="amber"
          />
          <ScoreGauge
            label="Performance Risk Score"
            description="V6 Full model — analyst-facing"
            score={player.performance_risk_score}
            color="primary"
          />
        </div>

        {/* Minutes breakdown */}
        <div className="bg-card border border-border rounded-xl p-6">
          <h3 className="font-semibold mb-4">Minutes Load Breakdown</h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {minuteStats.map(s => (
              <div key={s.label} className="text-center">
                <div className="text-xs text-muted-foreground mb-1">{s.label}</div>
                <div className="text-xl font-bold text-primary">{s.value ?? "—"}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Workload Timeline */}
        <WorkloadTimeline data={player.workload_timeline || []} />

        {/* Action Load + Injury Context */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <ActionLoadBreakdown player={player} />
          <InjuryContext player={player} />
        </div>

        {/* Rating context */}
        {(player.avg_rating_last_3 || player.avg_rating_last_5) && (
          <div className="bg-card border border-border rounded-xl p-6">
            <h3 className="font-semibold mb-4">Recent Rating Baseline</h3>
            <div className="grid grid-cols-2 gap-6">
              <div className="text-center">
                <div className="text-xs text-muted-foreground mb-1">Avg Rating (Last 3)</div>
                <div className="text-2xl font-bold text-chart-4">{player.avg_rating_last_3?.toFixed(2) ?? "—"}</div>
              </div>
              <div className="text-center">
                <div className="text-xs text-muted-foreground mb-1">Avg Rating (Last 5)</div>
                <div className="text-2xl font-bold text-chart-4">{player.avg_rating_last_5?.toFixed(2) ?? "—"}</div>
              </div>
            </div>
            <p className="text-xs text-muted-foreground mt-3">
              Note: Rating baseline influences the Performance Risk Score only. The Workload/Fatigue Score excludes these to remain a pure load-based signal.
            </p>
          </div>
        )}

      </div>
    </div>
  );
}
