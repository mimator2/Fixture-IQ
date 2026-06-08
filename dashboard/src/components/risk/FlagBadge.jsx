import { flagLabels } from "./RiskBadge";

const flagColors = {
  short_recovery:             "bg-chart-5/10 text-chart-5 border-chart-5/20",
  high_action_load:           "bg-chart-4/10 text-chart-4 border-chart-4/20",
  recent_ucl_minutes:         "bg-primary/10 text-primary border-primary/20",
  high_squad_injury_pressure: "bg-red-400/10 text-red-400 border-red-400/20",
  returning_from_injury:      "bg-accent/10 text-accent border-accent/20",
};

export default function FlagBadge({ flag }) {
  const label = flagLabels[flag] || flag;
  const cls = flagColors[flag] || "bg-muted text-muted-foreground border-border";
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${cls}`}>
      {label}
    </span>
  );
}