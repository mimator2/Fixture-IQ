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

const POSITION_METRICS = {
  Defender: [
    { label: "Tackles (last 3)",         key: "tackles_last_3",   highlight: v => v > 15 },
    { label: "Tackles (last 14d)",       key: "tackles_last_14",  highlight: v => v > 25 },
    { label: "Duels (last 3)",           key: "duels_last_3",     highlight: v => v > 25 },
    { label: "Duels (last 14d)",         key: "duels_last_14",    highlight: v => v > 40 },
    { label: "Fouls (last 3)",           key: "fouls_last_3",     highlight: v => v > 6  },
    { label: "Fouls (last 14d)",         key: "fouls_last_14",    highlight: v => v > 10 },
    { label: "Cards (last 5)",           key: "cards_last_5",     highlight: v => v > 3  },
  ],
  Midfielder: [
    { label: "Duels (last 3)",           key: "duels_last_3",     highlight: v => v > 25 },
    { label: "Duels (last 14d)",         key: "duels_last_14",    highlight: v => v > 40 },
    { label: "Dribbles (last 3)",        key: "dribbles_last_3",  highlight: v => v > 10 },
    { label: "Dribbles (last 14d)",      key: "dribbles_last_14", highlight: v => v > 20 },
    { label: "Tackles (last 3)",         key: "tackles_last_3",   highlight: v => v > 12 },
    { label: "Tackles (last 14d)",       key: "tackles_last_14",  highlight: v => v > 20 },
    { label: "Fouls (last 3)",           key: "fouls_last_3",     highlight: v => v > 5  },
    { label: "Cards (last 5)",           key: "cards_last_5",     highlight: v => v > 3  },
  ],
  Forward: [
    { label: "Dribbles (last 3)",        key: "dribbles_last_3",  highlight: v => v > 10 },
    { label: "Dribbles (last 14d)",      key: "dribbles_last_14", highlight: v => v > 20 },
    { label: "Duels (last 3)",           key: "duels_last_3",     highlight: v => v > 20 },
    { label: "Duels (last 14d)",         key: "duels_last_14",    highlight: v => v > 35 },
    { label: "Fouls (last 3)",           key: "fouls_last_3",     highlight: v => v > 4  },
    { label: "Cards (last 5)",           key: "cards_last_5",     highlight: v => v > 2  },
  ],
};


export default function MatchActionsSection({ player }) {
  const metrics = POSITION_METRICS[player.position] ?? null;

  return (
    <div className="bg-card border border-border rounded-xl p-5 relative">
      <div className="flex items-center gap-2 mb-4">
        <Zap className="w-4 h-4 text-primary" />
        <h3 className="font-semibold">Match Actions</h3>
      </div>
      
      {metrics === null ? (
        <p className="text-sm text-muted-foreground">Match action metrics not tracked for goalkeepers.</p>
      ) : (
        <div className="relative group"> {/* Added 'group' to handle hover transitions if needed */}
          {/* Scrollable container */}
          <div className="max-h-[280px] overflow-y-auto pr-2 space-y-1 pb-8
            [&::-webkit-scrollbar]:w-[3px] 
            [&::-webkit-scrollbar-track]:bg-transparent 
            [&::-webkit-scrollbar-thumb]:bg-muted-foreground/30 
            [&::-webkit-scrollbar-thumb]:rounded-full">
            
            {metrics.map(m => (
              <Row key={m.key} label={m.label} value={player[m.key]} highlight={m.highlight(player[m.key] ?? 0)} />
            ))}
            <Row label="Physical Load Index" value={player.physical_load_index?.toFixed(1)} highlight={(player.physical_load_index ?? 0) > 15} help={METRIC_HELP.pli} />
            <Row label="Tackles z-score (pos)" value={player.tackles_total_position_z?.toFixed(2)} highlight={(player.tackles_total_position_z ?? 0) > 1} help={METRIC_HELP.action_load_zscore} />
            <Row label="Duels z-score (pos)" value={player.duels_total_position_z?.toFixed(2)} highlight={(player.duels_total_position_z ?? 0) > 1} />
            <Row label="Minutes z-score (pos)" value={player.minutes_played_position_z?.toFixed(2)} highlight={(player.minutes_played_position_z ?? 0) > 1} />
            <Row label="Fouls z-score (pos)" value={player.fouls_committed_position_z?.toFixed(2)} highlight={(player.fouls_committed_position_z ?? 0) > 1} />
            <Row label="PLI vs season avg" value={player.physical_load_last_14d_vs_player_avg?.toFixed(2)} highlight={(player.physical_load_last_14d_vs_player_avg ?? 0) > 0.5} />
          </div>

          {/* Clean Gradient Fade */}
          <div className="absolute bottom-0 left-0 right-0 h-10 bg-gradient-to-t from-card to-transparent pointer-events-none" />
        </div>
      )}
    </div>
  );
}

