import { Users } from "lucide-react";
import InfoTip, { METRIC_HELP } from "@/components/ui/InfoTip";

const Row = ({ label, value, highlight, help }) => (
  <div className="flex items-center justify-between py-2 border-b border-border last:border-0">
    <span className="text-sm text-muted-foreground flex items-center">
      {label}
      {help && <InfoTip text={help} />}
    </span>
    <span className={`text-sm font-semibold ${highlight ? "text-red-400" : "text-foreground"}`}>{value ?? "—"}</span>
  </div>
);

export default function SquadContextSection({ player }) {
  return (
    <div className="bg-card border border-border rounded-xl p-5">
      <div className="flex items-center gap-2 mb-4">
        <Users className="w-4 h-4 text-primary" />
        <h3 className="font-semibold">Squad Context</h3>
      </div>
      <div>
        <Row label="Squad injured"           value={player.squad_injured_count}    highlight={(player.squad_injured_count ?? 0) >= 4} />
        <Row label="Soft tissue injuries"    value={player.squad_soft_tissue_count} highlight={(player.squad_soft_tissue_count ?? 0) >= 2} />
        <Row label="Avg days out"            value={player.squad_avg_days_out != null ? `${player.squad_avg_days_out}d` : null} highlight={(player.squad_avg_days_out ?? 0) > 14} />
        <Row label="Returning from injury"   value={player.returning_from_injury ? "Yes" : "No"} highlight={player.returning_from_injury} />
        <Row label="Days since last injury"  value={player.days_since_last_injury != null ? `${player.days_since_last_injury}d` : null} highlight={player.days_since_last_injury != null && player.days_since_last_injury < 21} />
        <Row label="Injury context score"    value={player.injury_context_score?.toFixed(1)} highlight={(player.injury_context_score ?? 0) > 4} help={METRIC_HELP.injury_context_score} />
      </div>
    </div>
  );
}