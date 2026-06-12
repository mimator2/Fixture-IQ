import { Clock } from "lucide-react";
import InfoTip, { METRIC_HELP } from "@/components/ui/InfoTip";

const Row = ({ label, value, highlight, help }) => (
  <div className="flex items-center justify-between py-2 border-b border-border last:border-0">
    <span className="text-sm text-muted-foreground flex items-center gap-1">
      {label}
      {help && <InfoTip text={help} />}
    </span>
    <span className={`text-sm font-semibold ${highlight ? "text-chart-4" : "text-foreground"}`}>{value ?? "—"}</span>
  </div>
);

export default function WorkloadSection({ player }) {
  return (
    <div className="bg-card border border-border rounded-xl p-5 relative">
      <div className="flex items-center gap-2 mb-4">
        <Clock className="w-4 h-4 text-primary" />
        <h3 className="font-semibold">Workload Context</h3>
      </div>
      
      {/* Wrapped in a relative container so the absolute fade pins exactly to the rows */}
      <div className="relative group"> 
        {/* Scrollable wrapper container */}
          <div className="max-h-[280px] overflow-y-auto pr-2 space-y-1 pb-8
            [&::-webkit-scrollbar]:w-[3px] 
            [&::-webkit-scrollbar-track]:bg-transparent 
            [&::-webkit-scrollbar-thumb]:bg-muted-foreground/30 
            [&::-webkit-scrollbar-thumb]:rounded-full"
        >
          <Row label="Minutes last 14d"          value={player.minutes_last_14}                highlight={(player.minutes_last_14 ?? 0) > 180} />
          <Row label="Minutes last 21d"          value={player.minutes_last_21}                highlight={(player.minutes_last_21 ?? 0) > 270} />
          <Row label="Minutes last 28d"          value={player.minutes_last_28}                highlight={(player.minutes_last_28 ?? 0) > 360} />
          <Row label="Starts (last 14d)"          value={player.starts_last_14}                 highlight={(player.starts_last_14 ?? 0) >= 5} />
          <Row label="Starts (last 28d)"          value={player.starts_last_28}                 highlight={(player.starts_last_28 ?? 0) >= 8} />
          <Row label="Full 90s (last 14d)"       value={player.full_90s_last_14}               highlight={(player.full_90s_last_14 ?? 0) >= 4} />
          <Row label="Full 90s (last 28d)"       value={player.full_90s_last_28}               highlight={(player.full_90s_last_28 ?? 0) >= 6} />
          <Row label="Rest days"                 value={player.rest_days != null ? `${player.rest_days}d` : null} highlight={(player.rest_days ?? 99) < 3} />
          <Row label="Avg rest days (last 5)"    value={player.avg_rest_days_last_5 != null ? `${player.avg_rest_days_last_5}d` : null} highlight={(player.avg_rest_days_last_5 ?? 99) < 3.5} />
          <Row label="Short-rest matches (30d)"  value={player.short_rest_matches_30d}          highlight={(player.short_rest_matches_30d ?? 0) >= 3} help={METRIC_HELP.short_rest_matches} />
        </div>

        {/* Clean, low-profile bottom gradient fade pinned perfectly to the content area */}
        <div className="absolute bottom-0 left-0 right-0 h-10 bg-gradient-to-t from-card to-transparent pointer-events-none" />
      </div>
    </div>
  );
}