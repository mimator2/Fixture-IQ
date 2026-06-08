export default function ScoreGauge({ label, score, color = "primary", description }) {
  const raw = score ?? 0;
  const pct = Math.min(100, Math.max(0, raw * 100));
  const colorMap = {
    primary: "from-primary to-primary/60",
    amber:   "from-chart-4 to-chart-4/60",
    red:     "from-chart-5 to-chart-5/60",
    teal:    "from-accent to-accent/60",
  };
  const textMap = {
    primary: "text-primary",
    amber:   "text-chart-4",
    red:     "text-chart-5",
    teal:    "text-accent",
  };
  return (
    <div className="bg-card border border-border rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">{label}</div>
          {description && <div className="text-xs text-muted-foreground mt-0.5">{description}</div>}
        </div>
        <div className={`text-2xl font-bold ${textMap[color]}`}>{raw.toFixed(3)}</div>
      </div>
      <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full bg-gradient-to-r ${colorMap[color]} transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
