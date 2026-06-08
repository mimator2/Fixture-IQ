import { useHypotheses } from "@/hooks/useHypotheses";
import { CheckCircle2, AlertCircle, HelpCircle, Clock } from "lucide-react";

const statusConfig = {
  "Supported": { icon: CheckCircle2, color: "text-chart-3", bg: "bg-chart-3/10", border: "border-chart-3/20" },
  "Partially Supported": { icon: AlertCircle, color: "text-chart-4", bg: "bg-chart-4/10", border: "border-chart-4/20" },
  "Not Supported": { icon: HelpCircle, color: "text-chart-5", bg: "bg-chart-5/10", border: "border-chart-5/20" },
  "Pending": { icon: Clock, color: "text-muted-foreground", bg: "bg-muted", border: "border-border" },
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
              <>
                <p className="text-sm text-muted-foreground mb-3 leading-relaxed">{h.description}</p>
                {h.evidence_summary && (
                  <div className="bg-muted/50 rounded-lg p-3 border border-border">
                    <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">Evidence</div>
                    <p className="text-sm text-foreground/80 leading-relaxed">{h.evidence_summary}</p>
                  </div>
                )}
                {h.key_metric && h.key_value && (
                  <div className="mt-3 flex items-center gap-2 text-xs">
                    <span className="text-muted-foreground">{h.key_metric}:</span>
                    <span className="font-semibold text-primary">{h.key_value}</span>
                  </div>
                )}
              </>
            )}
          </div>
        );
      })}
    </div>
  );
}
