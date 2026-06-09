import { Zap } from "lucide-react";
import InfoTip, { METRIC_HELP } from "@/components/ui/InfoTip";

const Row = ({ label, value, highlight, help }) => (
  <div className="flex items-center justify-between py-2 border-b border-border last:border-0">
    <span className="text-sm text-muted-foreground flex items-center">
      {label}
      {help && <InfoTip text={help} />}
    </span>
    <span className={`text-sm font-semibold ${highlight ? "text-chart-4" : "text-foreground"}`}>{value ?? "—"}</span>
  </div>
);

export default function PhysicalEffortSection({ player }) {
  return (
    <div className="bg-card border border-border rounded-xl p-5">
      <div className="flex items-center gap-2 mb-4">
        <Zap className="w-4 h-4 text-primary" />
        <h3 className="font-semibold">Physical Effort</h3>
      </div>
      <div>
        <Row label="Duels (last 5)"      value={player.duels_last_5}        highlight={(player.duels_last_5 ?? 0) > 40} />
        <Row label="Tackles (last 5)"    value={player.tackles_last_5}      highlight={(player.tackles_last_5 ?? 0) > 20} />
        <Row label="Dribbles (last 5)"   value={player.dribbles_last_5}     highlight={(player.dribbles_last_5 ?? 0) > 15} />
        <Row label="Shots (last 5)"      value={player.shots_last_5}        highlight={(player.shots_last_5 ?? 0) > 15} />
        <Row label="Key passes (last 5)" value={player.key_passes_last_5}   highlight={false} />
        <Row label="Physical Load Index" value={player.physical_load_index?.toFixed(1)} highlight={(player.physical_load_index ?? 0) > 15} help={METRIC_HELP.pli} />
        <Row label="Action Load Z-Score" value={player.recent_action_load_per90_pos_z?.toFixed(2)} highlight={(player.recent_action_load_per90_pos_z ?? 0) > 1} help={METRIC_HELP.action_load_zscore} />
      </div>
    </div>
  );
}