import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { Info } from "lucide-react";

export default function InfoTip({ text, side = "top" }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button type="button" className="inline-flex items-center ml-1 text-muted-foreground/50 hover:text-muted-foreground transition-colors cursor-help">
          <Info className="w-3 h-3" />
        </button>
      </TooltipTrigger>
      <TooltipContent side={side} className="max-w-64 text-xs leading-relaxed">
        {text}
      </TooltipContent>
    </Tooltip>
  );
}

export const METRIC_HELP = {
  fatigue_score: "Workload/Fatigue Score (V6 No Rating Baseline) — pure load-based signal from minutes, rest, and fixture density. Excludes performance ratings. Coach-facing metric.",
  performance_risk_score: "Performance Risk Score (V6 Full) — includes all features plus rating baselines. Better for analyst review. A higher score means higher injury/probability risk.",
  monitoring_threshold: "The composite score threshold above which a player is flagged for monitoring. Calculated from model calibration. Players above this threshold appear in High/Very High bands.",
  risk_flags: "Automated flags triggered when specific feature values cross predefined thresholds. Each flag represents a distinct risk signal that staff should review.",
  physical_load_index: "Weighted composite of duels (×1.5), tackles (×1.2), dribbles (×1.1), shots (×0.8), and key passes (×0.5) averaged over 5 matches. A proxy for physical effort where GPS data is unavailable.",
  action_load_zscore: "Z-score of the player's recent action load per 90 minutes compared to positional peers. A value > 1 means the player is one standard deviation above their position average — elevated physical demand.",
  minutes_zscore: "Z-score of the player's recent minutes compared to positional peers. A value > 1 means minutes are one standard deviation above their position average — high minutes load for their role.",
  injury_context_score: "Composite score (0–10) combining squad injury count, soft-tissue injuries, avg days out, and returning-from-injury status. Higher values indicate elevated squad-level injury pressure.",
  short_rest_matches: "Number of matches in the last 30 days where the player had 4 or fewer days of rest between appearances. ≥3 is considered high and flagged as a workload concern.",
  competition_switches: "Number of different competitions (Premier League, UCL, Cup) the player has appeared in over the last 21 days. Multiple switches increase fixture density and recovery complexity.",
  pli: "Physical Load Index — a simplified metric calculated from available event data (duels, tackles, dribbles, shots, key passes). Position-normalized baselines are planned when full dataset is available.",
  rotation_pct: "Percentage of squad players classified as Rotation Player vs Core Starter. A higher percentage indicates a team that rotates its squad more frequently across matches.",
};
