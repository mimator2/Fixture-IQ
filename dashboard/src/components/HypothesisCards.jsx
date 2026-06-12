import { useHypotheses } from "@/hooks/useHypotheses";
import { CheckCircle2, AlertCircle, HelpCircle, Clock } from "lucide-react";

const statusConfig = {
  "Supported": { icon: CheckCircle2, color: "text-chart-3", bg: "bg-chart-3/10", border: "border-chart-3/20" },
  "Partially Supported": { icon: AlertCircle, color: "text-chart-4", bg: "bg-chart-4/10", border: "border-chart-4/20" },
  "Not Supported": { icon: HelpCircle, color: "text-chart-5", bg: "bg-chart-5/10", border: "border-chart-5/20" },
  "Pending": { icon: Clock, color: "text-muted-foreground", bg: "bg-muted", border: "border-border" },
};

const CONCLUSIONS = {
  "H1": "H1 tests whether short rest (≤3d) alone predicts worse next-match performance, under two views: (1) scorable appearances (minutes_played ≥45) and (2) full population (all minutes). The results show no meaningful rating drop under short rest in either view—confirming that simple single-heuristic fatigue rules underestimate the complexity of congestion effects and justifying the V4B model's multivariate approach.",
  "H2": "Rotation is inversely related to available rest. During congested periods, managers rely on a settled XI rather than rotating, which paradoxically increases individual player load accumulation — the exact condition the V4B model is designed to detect. Squad rotation is a strategic response to fixture density, not random variation.",
  "H3": "European involvement modifies rotation behaviour, but it is not deterministic. Squad depth and managerial approach are significant moderators. The V4B model captures this through dedicated competition-transition features (transition_ucl_to_pl, pl_after_ucl_with_short_rest) rather than simple binary competition flags.",
  "H4": "The previous three hypotheses establish that fixture congestion has measurable, complex effects on performance and squad behaviour. H4 is the natural next step: studying whether the dashboard's risk scores and SHAP explanations actually change staff behaviour. This requires a controlled longitudinal study with coaching and medical teams — impossible to evaluate from historical match data alone.",
};

export default function HypothesisCards({ compact = false }) {
  const { data: hypotheses = [], isLoading } = useHypotheses();

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="bg-card border border-border rounded-xl p-5 animate-pulse h-40" />
        ))}
      </div>
    );
  }

  const sorted = [...hypotheses].sort((a, b) => (a.hypothesis_id || "").localeCompare(b.hypothesis_id || ""));

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {sorted.map((h) => {
        const config = statusConfig[h.status] || statusConfig["Pending"];
        const Icon = config.icon;
        const conclusion = h.conclusion || CONCLUSIONS[h.hypothesis_id];
        return (
          <div
            key={h.id}
            className={`bg-card border rounded-xl p-5 ${config.border} hover:border-primary/30 transition-colors`}
          >
            <div className="flex items-start gap-3 mb-3">
              <div className={`w-8 h-8 rounded-lg ${config.bg} flex items-center justify-center shrink-0 mt-0.5`}>
                <Icon className={`w-4 h-4 ${config.color}`} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-mono font-semibold text-primary">{h.hypothesis_id}</span>
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${config.bg} ${config.color}`}>
                    {h.status}
                  </span>
                </div>
                <h4 className="font-semibold text-sm">{h.title}</h4>
              </div>
            </div>

            {!compact && (
              <div className="space-y-3">
                {h.evidence_summary && (
                  <div className="bg-muted/50 rounded-lg p-3 border border-border">
                    <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">Evidence</div>
                    <p className="text-sm text-foreground/80 leading-relaxed">{h.evidence_summary}</p>
                    {h.key_metric && h.key_value && (
                      <div className="mt-2 flex items-center gap-2 text-xs">
                        <span className="text-muted-foreground">{h.key_metric}:</span>
                        <span className="font-semibold text-primary">{h.key_value}</span>
                      </div>
                    )}
                  </div>
                )}
                {conclusion && (
                  <div className="bg-muted/30 rounded-lg p-3 border border-border/50">
                    <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">Conclusion</div>
                    <p className="text-sm text-foreground/80 leading-relaxed">{conclusion}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
