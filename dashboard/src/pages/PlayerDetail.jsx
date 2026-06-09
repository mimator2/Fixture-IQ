import { useState, useMemo, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { usePlayerRisk } from "@/hooks/usePlayerRisks";
import RiskBadge from "@/components/risk/RiskBadge";
import FlagBadge from "@/components/risk/FlagBadge";
import ScoreGauge from "@/components/risk/ScoreGauge";
import PlayerExplanation from "@/components/risk/PlayerExplanation";
import WorkloadSection from "@/components/risk/WorkloadSection";
import CompetitionSection from "@/components/risk/CompetitionSection";
import PhysicalEffortSection from "@/components/risk/PhysicalEffortSection";
import SquadContextSection from "@/components/risk/SquadContextSection";
import WorkloadTimeline from "@/components/risk/WorkloadTimeline";
import InfoTip, { METRIC_HELP } from "@/components/ui/InfoTip";
import { ArrowLeft, Shield, Activity, AlertTriangle, Gauge, BrainCircuit, Calendar } from "lucide-react";

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
  const [showTimeline, setShowTimeline] = useState(false);
  const [timelineData, setTimelineData] = useState([]);

  useEffect(() => {
    if (showTimeline && timelineData.length === 0 && player) {
      fetch(`/data/player_timelines/${player.id}.json`)
        .then(r => r.ok ? r.json() : [])
        .then(setTimelineData)
        .catch(() => setTimelineData([]));
    }
  }, [showTimeline, player?.id]);

  const playerExplanation = useMemo(
    () => player ? <PlayerExplanation player={player} /> : null,
    [player?.id]
  );
  const sectionsGrid = useMemo(
    () => player ? (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <WorkloadSection player={player} />
        <CompetitionSection player={player} />
        <PhysicalEffortSection player={player} />
        <SquadContextSection player={player} />
      </div>
    ) : null,
    [player?.id]
  );

  if (isLoading) return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-4">
      {[1,2,3].map(i => <div key={i} className="bg-card border border-border rounded-xl h-40 animate-pulse" />)}
    </div>
  );

  if (!player) return (
    <div className="max-w-5xl mx-auto px-4 py-12 text-center text-muted-foreground">Player not found.</div>
  );

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
            <div className="flex flex-col items-end gap-2">
              <div className={`px-4 py-2 rounded-lg border text-sm font-medium ${actionCls} text-center max-w-56`}>
                {player.recommended_action}
              </div>
              <Link
                to={`/model/${player.id}`}
                className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-primary transition-colors"
              >
                <BrainCircuit className="w-3.5 h-3.5" />
                View model drivers
              </Link>
            </div>
          </div>
        </div>

        {/* A. Current Risk Assessment */}
        <div>
          <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
            <Activity className="w-4 h-4 text-primary" />
            Current Risk Assessment
          </h2>
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
          <div className="grid grid-cols-3 gap-3 mt-3">
            <div className="bg-muted/30 rounded-lg p-3 text-center">
              <div className="flex items-center justify-center gap-1.5 mb-1">
                <AlertTriangle className="w-3.5 h-3.5 text-chart-5" />
                <span className="text-xs text-muted-foreground">Risk Band</span>
              </div>
              <div className={`text-lg font-bold ${player.risk_band === "High" || player.risk_band === "Very High" ? "text-chart-5" : "text-chart-3"}`}>{player.risk_band}</div>
            </div>
            <div className="bg-muted/30 rounded-lg p-3 text-center">
              <div className="flex items-center justify-center gap-1.5 mb-1">
                <Shield className="w-3.5 h-3.5 text-primary" />
                <span className="text-xs text-muted-foreground">Monitoring Flag</span>
                <InfoTip text={METRIC_HELP.risk_flags} />
              </div>
              <div className={`text-lg font-bold ${player.risk_flags?.length ? "text-chart-5" : "text-chart-3"}`}>{player.risk_flags?.length ? "Active" : "Clear"}</div>
            </div>
            <div className="bg-muted/30 rounded-lg p-3 text-center">
              <div className="flex items-center justify-center gap-1.5 mb-1">
                <Gauge className="w-3.5 h-3.5 text-primary" />
                <span className="text-xs text-muted-foreground">Threshold</span>
                <InfoTip text={METRIC_HELP.monitoring_threshold} />
              </div>
              <div className="text-lg font-bold text-primary">{player.monitoring_threshold?.toFixed(3) ?? "—"}</div>
            </div>
          </div>
        </div>

        {/* Player Explanation — rule-based SHAP proxy */}
        {playerExplanation}

        {/* B–E: Section components */}
        {sectionsGrid}

        {/* Workload Timeline — opt-in to avoid chart rendering slowdown */}
        <div className="bg-card border border-border rounded-xl p-5">
          <button
            onClick={() => setShowTimeline(!showTimeline)}
            className="flex items-center gap-2 w-full text-left"
          >
            <Calendar className="w-4 h-4 text-chart-4" />
            <span className="font-semibold text-sm">Workload Timeline</span>
            <span className="ml-auto text-xs text-muted-foreground">{showTimeline ? "▲" : "▼"}</span>
          </button>
          {showTimeline && (
            <div className="mt-4 space-y-3">
              <p className="text-xs text-muted-foreground bg-muted/30 rounded-lg px-3 py-2">
                The timeline chart renders ~20 data points per player and may briefly impact page responsiveness.
              </p>
              <WorkloadTimeline data={timelineData} />
            </div>
          )}
        </div>

        {/* Rating context */}
        {(player.avg_rating_last_3 || player.avg_rating_last_5) && (
          <div className="bg-card border border-border rounded-xl p-6">
            <h3 className="font-semibold mb-4">Recent Rating Baseline</h3>
            <div className="grid grid-cols-2 gap-6">
              <div className="bg-muted/30 rounded-lg p-3 text-center">
                <div className="text-xs text-muted-foreground mb-1">Avg Rating (Last 3)</div>
                <div className="text-lg font-bold text-chart-4">{player.avg_rating_last_3?.toFixed(2) ?? "—"}</div>
              </div>
              <div className="bg-muted/30 rounded-lg p-3 text-center">
                <div className="text-xs text-muted-foreground mb-1">Avg Rating (Last 5)</div>
                <div className="text-lg font-bold text-chart-4">{player.avg_rating_last_5?.toFixed(2) ?? "—"}</div>
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
