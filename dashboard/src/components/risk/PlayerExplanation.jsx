import { Lightbulb } from "lucide-react";

function buildShapDrivers(player) {
  const raw = player.shap_drivers_perf || player.shap_drivers_fatigue || [];
  return raw.slice(0, 5).map((d) => ({
    feature: d.feature,
    value: d.value,
    contribution: d.contribution,
    text: `${d.feature} = ${d.value}`,
    weight: Math.round(Math.min(100, Math.abs(d.contribution) * 500)),
  }));
}

function buildExplanations(player) {
  const reasons = [];

  const shortRest4 = player.short_rest_matches_30d ?? 0;
  const shortRest6 = player.matches_with_rest_le_6d_last_30d ?? 0;
  if (shortRest4 >= 2) reasons.push({ weight: 100, text: `${shortRest4} match${shortRest4 > 1 ? "es" : ""} with ≤4 days rest in the last 30 days`, feature: "matches_with_rest_le_4d_last_30d" });
  else if (shortRest6 >= 3) reasons.push({ weight: 88, text: `${shortRest6} matches with ≤6 days rest in the last 30 days`, feature: "matches_with_rest_le_6d_last_30d" });

  if ((player.full_90s_last_5 ?? 0) >= 4)
    reasons.push({ weight: 79, text: `${player.full_90s_last_5} full-90 appearances in recent matches`, feature: "full_90s_last_14d" });

  if ((player.ucl_minutes_last_21 ?? 0) >= 90)
    reasons.push({ weight: 52, text: `${player.ucl_minutes_last_21} UCL minutes in the last 21 days`, feature: "ucl_matches_last_30d" });

  if ((player.avg_rest_days_last_5 ?? 99) < 3.5)
    reasons.push({ weight: 65, text: `Average rest of ${player.avg_rest_days_last_5?.toFixed(1)} days between recent matches`, feature: "rest_days" });

  if (player.days_since_last_european != null && player.days_since_last_european <= 4 && (player.ucl_minutes_last_21 ?? 0) > 0)
    reasons.push({ weight: 52, text: "Next match follows UCL fixture with short recovery window", feature: "ucl_matches_last_30d" });

  if ((player.starts_last_5 ?? 0) === 5)
    reasons.push({ weight: 58, text: "5 consecutive starts — no rotation in recent run", feature: "starts_last_14d" });

  if ((player.squad_soft_tissue_count ?? 0) >= 2)
    reasons.push({ weight: 44, text: `${player.squad_soft_tissue_count} soft-tissue injuries in squad — elevated cover pressure`, feature: "squad_soft_tissue_count" });

  if (player.returning_from_injury)
    reasons.push({ weight: 31, text: `Returning from injury (${player.days_since_last_injury ?? "?"} days ago) — post-injury vulnerability window`, feature: "returning_from_injury" });

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
    ? "SHAP TreeExplainer feature contributions"
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
              <div className="flex-1 min-w-0">
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
          ? "SHAP TreeExplainer local values from the CatBoost model — feature contributions to the V6 risk score."
          : "In production: replace with SHAP TreeExplainer local values from the CatBoost model artefact for fully grounded explanations."}
      </p>
    </div>
  );
}