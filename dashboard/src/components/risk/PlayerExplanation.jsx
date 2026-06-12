import { Lightbulb } from "lucide-react";

const FEATURE_LABELS = {
  rest_days: "Rest days since last match",
  acwr_ratio: "Acute:chronic workload ratio",
  consecutive_away_games: "Consecutive away games",
  min_last_7d: "Minutes played (last 7 days)",
  min_last_14d: "Minutes played (last 14 days)",
  min_last_21d: "Minutes played (last 21 days)",
  min_last_28d: "Minutes played (last 28 days)",
  starts_last_7d: "Starts (last 7 days)",
  starts_last_14d: "Starts (last 14 days)",
  starts_last_28d: "Starts (last 28 days)",
  full_90s_last_7d: "Full-90 appearances (last 7 days)",
  full_90s_last_14d: "Full-90 appearances (last 14 days)",
  full_90s_last_28d: "Full-90 appearances (last 28 days)",
  short_rest_last_3_matches: "Short-rest matches in last 3",
  avg_rest_last_3_matches: "Avg rest between recent matches",
  min_rest_last_3_matches: "Minimum rest between recent matches",
  matches_with_rest_le_3d_last_30d: "Matches with ≤3 days rest (last 30d)",
  matches_with_rest_le_4d_last_30d: "Matches with ≤4 days rest (last 30d)",
  matches_with_rest_le_6d_last_30d: "Matches with ≤6 days rest (last 30d)",
  matches_last_7d: "Matches played (last 7 days)",
  matches_last_14d: "Matches played (last 14 days)",
  matches_last_21d: "Matches played (last 21 days)",
  matches_last_28d: "Matches played (last 28 days)",
  high_congestion_flag: "High fixture congestion period",
  ucl_minutes_last_7d: "UCL minutes (last 7 days)",
  ucl_minutes_last_14d: "UCL minutes (last 14 days)",
  ucl_minutes_last_21d: "UCL minutes (last 21 days)",
  ucl_starts_last_14d: "UCL starts (last 14 days)",
  ucl_full90s_last_14d: "UCL full-90s (last 14 days)",
  ucl_matches_last_30d: "UCL matches (last 30 days)",
  days_since_last_ucl: "Days since last UCL match",
  played_ucl_last_match: "Played in UCL last match",
  cup_minutes_last_7d: "Cup minutes (last 7 days)",
  cup_minutes_last_14d: "Cup minutes (last 14 days)",
  cup_starts_last_14d: "Cup starts (last 14 days)",
  cup_full90s_last_14d: "Cup full-90s (last 14 days)",
  cup_matches_last_30d: "Cup matches (last 30 days)",
  played_domestic_cup_last_match: "Played in domestic cup last match",
  transition_ucl_to_pl: "Transition from UCL to PL",
  transition_pl_to_ucl: "Transition from PL to UCL",
  transition_cup_to_pl: "Transition from Cup to PL",
  transition_pl_to_cup: "Transition from PL to Cup",
  competition_switches_last_30d: "Competition switches (last 30 days)",
  competitions_played_last_30d: "Competitions played (last 30 days)",
  rest_days_after_ucl: "Rest days after UCL match",
  post_ucl_short_rest: "Post-UCL short recovery window",
  pl_after_ucl_with_short_rest: "PL match after UCL with short rest",
  ucl_full90_then_pl_short_rest: "Full UCL match then PL with short rest",
  days_since_european_match: "Days since last European match",
  matches_since_european_match: "Matches since last European match",
  duels_last_3_matches: "Duels (last 3 matches)",
  duels_last_14d: "Duels (last 14 days)",
  tackles_last_3_matches: "Tackles (last 3 matches)",
  tackles_last_14d: "Tackles (last 14 days)",
  fouls_last_3_matches: "Fouls (last 3 matches)",
  fouls_last_14d: "Fouls (last 14 days)",
  dribbles_last_3_matches: "Dribbles (last 3 matches)",
  dribbles_last_14d: "Dribbles (last 14 days)",
  cards_last_5_matches: "Cards (last 5 matches)",
  duels_total_position_z: "Duels vs position average",
  tackles_total_position_z: "Tackles vs position average",
  fouls_committed_position_z: "Fouls vs position average",
  minutes_played_position_z: "Minutes vs position average",
  physical_load_index: "Physical load index (PLI)",
  minutes_last_21d_vs_player_avg: "Minutes vs player's season average",
  minutes_last_21d_player_z: "Minutes vs player's season average",
  full90_last_14d_vs_player_avg: "Full-90s vs player's season average",
  physical_load_last_14d_vs_player_avg: "Physical load vs player's season average",
  starts_last_14d_vs_player_avg: "Starts vs player's season average",
  squad_injured_count: "Squad injury burden",
  squad_soft_tissue_count: "Squad soft-tissue injuries",
  squad_avg_days_out: "Squad avg days out injured",
  returning_from_injury: "Returning from injury",
  fixtures_missed_last_30d: "Fixtures missed (last 30 days)",
  player_position_M: "Position: Midfielder",
  player_position_D: "Position: Defender",
  player_position_F: "Position: Forward",
  player_position_G: "Position: Goalkeeper",
  is_home: "Playing at home",
  is_substitute: "Came on as substitute",
};

function buildShapDrivers(player) {
  const raw = player.shap_drivers || [];
  return raw.slice(0, 5).map((d) => ({
    feature: d.feature,
    value: d.value,
    contribution: d.contribution,
    text: `${FEATURE_LABELS[d.feature] || d.feature}: ${d.value}`,
    weight: Math.round(Math.min(100, Math.abs(d.contribution) * 500)),
  }));
}

function buildExplanations(player) {
  const reasons = [];

  const shortRest4 = player.short_rest_matches_30d ?? 0;
  const shortRest6 = player.matches_with_rest_le_6d_last_30d ?? 0;
  if (shortRest4 >= 2) reasons.push({ weight: 100, text: `${shortRest4} match${shortRest4 > 1 ? "es" : ""} with ≤4 days rest in the last 30 days`, feature: "matches_with_rest_le_4d_last_30d" });
  else if (shortRest6 >= 3) reasons.push({ weight: 88, text: `${shortRest6} matches with ≤6 days rest in the last 30 days`, feature: "matches_with_rest_le_6d_last_30d" });

  if ((player.full_90s_last_14 ?? 0) >= 4)
    reasons.push({ weight: 79, text: `${player.full_90s_last_14} full-90 appearances in recent matches`, feature: "full_90s_last_14d" });

  if ((player.ucl_minutes_last_21 ?? 0) >= 90)
    reasons.push({ weight: 52, text: `${player.ucl_minutes_last_21} UCL minutes in the last 21 days`, feature: "ucl_matches_last_30d" });

  if ((player.avg_rest_days_last_5 ?? 99) < 3.5)
    reasons.push({ weight: 65, text: `Average rest of ${player.avg_rest_days_last_5?.toFixed(1)} days between recent matches`, feature: "rest_days" });

  if (player.days_since_last_european != null && player.days_since_last_european <= 4 && (player.ucl_minutes_last_21 ?? 0) > 0)
    reasons.push({ weight: 52, text: "Next match follows UCL fixture with short recovery window", feature: "ucl_matches_last_30d" });

  if ((player.starts_last_14 ?? 0) >= 5)
    reasons.push({ weight: 58, text: `${player.starts_last_14} starts in last 14 days — minimal rotation`, feature: "starts_last_14d" });

  if ((player.squad_soft_tissue_count ?? 0) >= 2)
    reasons.push({ weight: 44, text: `${player.squad_soft_tissue_count} soft-tissue injuries in squad — elevated cover pressure`, feature: "squad_soft_tissue_count" });

  if (player.returning_from_injury)
    reasons.push({ weight: 31, text: "Returning from injury — post-injury vulnerability window", feature: "returning_from_injury" });

  if ((player.physical_load_index ?? 0) > 15)
    reasons.push({ weight: 35, text: `High physical action load (PLI ${player.physical_load_index?.toFixed(1)}) — duels, tackles, dribbles above threshold`, feature: "physical_load_index" });

  if (reasons.length === 0 && player.main_risk_reasons) {
    reasons.push({ weight: 50, text: player.main_risk_reasons, feature: "main_risk_reasons" });
  }

  return reasons.sort((a, b) => b.weight - a.weight).slice(0, 5);
}

const BAND_INTRO = {
  "Very High": "This player shows multiple concurrent risk signals. Immediate staff review is recommended before the next match.",
  "High":      "This player is flagged with elevated workload indicators. Pre-match check recommended.",
  "Medium":    "This player has moderate workload signals. Monitor training response and wellness.",
  "Low":       "Load is within normal range. No specific intervention required.",
};

export default function PlayerExplanation({ player }) {
  const shapDrivers = buildShapDrivers(player);
  const useShap = shapDrivers.length > 0;
  const reasons = useShap ? shapDrivers : buildExplanations(player);
  const intro = BAND_INTRO[player.risk_band] || "";
  const subtitle = useShap
    ? "Top contributing factors to this player's risk score"
    : "rule-based feature explanation (SHAP proxy)";

  if (player.risk_band === "Low" && reasons.length === 0) {
    return (
      <div className="bg-chart-3/5 border border-chart-3/20 rounded-xl p-5 flex gap-3">
        <Lightbulb className="w-4 h-4 text-chart-3 mt-0.5 shrink-0" />
        <div>
          <div className="text-sm font-semibold text-chart-3 mb-1">Why this player is Low risk</div>
          <p className="text-sm text-muted-foreground">{intro}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-card border border-border rounded-xl p-5">
      <div className="flex items-center gap-2 mb-3">
        <Lightbulb className="w-4 h-4 text-chart-4" />
        <h3 className="font-semibold">Main Risk Drivers</h3>
        <span className="text-xs text-muted-foreground ml-1">— {subtitle}</span>
      </div>
      <p className="text-sm text-muted-foreground mb-4">{intro}</p>
      {reasons.length > 0 ? (
        <ol className="space-y-2">
          {reasons.map((r, i) => (
            <li key={i} className="flex items-start gap-3">
              <span className="w-5 h-5 rounded-full bg-primary/15 text-primary text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">
                {i + 1}
              </span>
              <div className="flex-1 min-w-0 max-w-[83%]">
                <span className="text-sm text-foreground/90">{r.text}</span>
                {useShap && (
                  <span className="text-xs text-muted-foreground block">
                    Contribution: +{r.contribution?.toFixed(4) ?? "?"}
                  </span>
                )}
                {/* <span className="text-xs text-muted-foreground ml-2 font-mono">({r.feature})</span> */}
              </div>
              <div className="w-20 h-1.5 bg-muted rounded-full overflow-hidden self-center shrink-0">
                <div className="h-full bg-primary/60 rounded-full" style={{ width: `${r.weight}%` }} />
              </div>
            </li>
          ))}
        </ol>
      ) : (
        <p className="text-sm text-muted-foreground">No dominant single feature — risk is distributed across multiple low-level signals.</p>
      )}
      <p className="text-xs text-muted-foreground mt-4 border-t border-border pt-3">
        {useShap
          ? "Each factor shows the current value and how much it contributes to the overall risk score."
          : "In production: replace with SHAP TreeExplainer local values from the XGBoost model artefact for fully grounded explanations."}
      </p>
    </div>
  );
}