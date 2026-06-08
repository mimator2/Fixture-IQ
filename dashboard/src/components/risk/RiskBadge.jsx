export const riskConfig = {
  "Low":       { color: "text-chart-3", bg: "bg-chart-3/15", border: "border-chart-3/30", dot: "bg-chart-3" },
  "Medium":    { color: "text-chart-4", bg: "bg-chart-4/15", border: "border-chart-4/30", dot: "bg-chart-4" },
  "High":      { color: "text-chart-5", bg: "bg-chart-5/15", border: "border-chart-5/30", dot: "bg-chart-5" },
  "Very High": { color: "text-red-400",  bg: "bg-red-400/15",  border: "border-red-400/30",  dot: "bg-red-400" },
};

export const flagLabels = {
  short_recovery:              "Short Recovery",
  high_action_load:            "High Action Load",
  recent_ucl_minutes:          "Recent UCL Minutes",
  high_squad_injury_pressure:  "Squad Injury Pressure",
  returning_from_injury:       "Returning from Injury",
};

export default function RiskBadge({ band, size = "sm" }) {
  const cfg = riskConfig[band] || riskConfig["Low"];
  const padding = size === "lg" ? "px-3 py-1 text-sm" : "px-2 py-0.5 text-xs";
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border font-semibold ${padding} ${cfg.bg} ${cfg.border} ${cfg.color}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
      {band}
    </span>
  );
}