import { useQuery } from "@tanstack/react-query";
import { useParams, Link } from "react-router-dom";
import { usePlayerRisk } from "@/hooks/usePlayerRisks";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import {
  Info, AlertTriangle, BarChart3, Layers, Shield, ArrowLeft,
} from "lucide-react";
import PlayerExplanation from "@/components/risk/PlayerExplanation";

const fetchJson = async (url) => {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to load ${url}`);
  return res.json();
};

function useModelMetadata() {
  return useQuery({
    queryKey: ["model-metadata"],
    queryFn: () => fetchJson("/data/model_metadata.json"),
    staleTime: 300_000,
  });
}

const GROUP_LABELS = {
  workload_recovery_windows: "Workload & Recovery Windows",
  competition_sequence_load: "Competition Sequence & Load",
  recent_action_load: "Recent Action Load",
  position_adjusted_load: "Position-Adjusted Load",
  injury_context: "Injury & Squad Context",
  role_context: "Role Context",
  missingness_context: "Data Missingness",
  recent_baseline_form: "Recent Baseline Form",
};

const GROUP_COLORS = {
  workload_recovery_windows: "text-chart-5",
  competition_sequence_load: "text-primary",
  recent_action_load: "text-chart-4",
  position_adjusted_load: "text-accent",
  injury_context: "text-red-400",
  role_context: "text-chart-3",
  missingness_context: "text-muted-foreground",
  recent_baseline_form: "text-chart-4",
};

export default function ModelExplanation() {
  const { playerId } = useParams();
  const { data: metadata, isLoading: metaLoading } = useModelMetadata();
  const { data: player } = usePlayerRisk(playerId);

  if (metaLoading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-8 space-y-4">
        {[1,2,3].map(i => <div key={i} className="bg-card border border-border rounded-xl h-40 animate-pulse" />)}
      </div>
    );
  }

  const fi = metadata?.feature_importances || [];
  const top20 = fi.slice(0, 20);
  const featureGroups = metadata?.feature_groups || {};
  const policy = metadata?.threshold_policy || {};

  const groupImportance = {};
  for (const [group, feats] of Object.entries(featureGroups)) {
    let total = 0;
    for (const feat of feats) {
      const found = fi.find(f => f.feature === feat);
      if (found) total += found.importance_pct;
    }
    groupImportance[group] = Math.round(total * 100) / 100;
  }
  const sortedGroups = Object.entries(groupImportance)
    .sort((a, b) => b[1] - a[1]);

  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    return (
      <div className="bg-popover border border-border rounded-lg p-3 shadow-xl text-sm">
        <p className="font-semibold text-foreground mb-1">{label}</p>
        {payload.map(e => (
          <p key={e.name} className="text-muted-foreground">
            {e.name}: <span className="font-medium text-foreground">{e.value.toFixed(2)}%</span>
          </p>
        ))}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-5xl mx-auto px-4 py-8 space-y-8">

        <div>
          <div className="flex items-center gap-2 mb-1">
            <BarChart3 className="w-5 h-5 text-primary" />
            <h1 className="text-2xl font-bold">Model Explanation</h1>
          </div>
          <p className="text-muted-foreground text-sm max-w-2xl">
            How the V4B XGBoost model assesses workload-associated risk — global feature drivers,
            player-specific contributors, threshold policy, and limitations.
          </p>
        </div>

        {/* A. Top global features */}
        <div className="bg-card border border-border rounded-xl p-6">
          <div className="flex items-center gap-2 mb-1">
            <BarChart3 className="w-4 h-4 text-primary" />
            <h3 className="font-semibold">Top Global Model Features</h3>
          </div>
          <p className="text-xs text-muted-foreground mb-4">
            Feature importance measured by XGBoost built-in importance (gain-weighted contribution to splits).
            The V4B profile is consistent with fatigue monitoring: workload and rest features dominate.
          </p>
          <div className="h-96">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={top20} layout="vertical" margin={{ left: 50, right: 100 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis type="number" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} domain={[0, "auto"]} />
                <YAxis type="category" dataKey="feature" interval={0} tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} width={180} tickFormatter={(v) => v.replace(/_/g, " ")} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="importance_pct" fill="hsl(var(--primary))" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* B. Feature Group Breakdown */}
        <div className="bg-card border border-border rounded-xl p-6">
          <div className="flex items-center gap-2 mb-1">
            <Layers className="w-4 h-4 text-primary" />
            <h3 className="font-semibold">Feature Group Contribution</h3>
          </div>
          <p className="text-xs text-muted-foreground mb-4">
            Aggregate importance by functional group. Workload and recent form are the dominant drivers.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {sortedGroups.length > 0 ? (
              sortedGroups.map(([group, pct]) => (
                <div key={group} className="bg-muted/30 rounded-lg p-3">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className={`text-xs font-semibold ${GROUP_COLORS[group] || "text-foreground"}`}>
                      {GROUP_LABELS[group] || group}
                    </span>
                    <span className="text-sm font-bold">{pct}%</span>
                  </div>
                  <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
                    <div className="h-full rounded-full" style={{ width: `${Math.min(100, pct)}%`, background: "hsl(217 91% 60%)" }} />
                  </div>
                </div>
              ))
            ) : (
                <div className="sm:col-span-2 bg-muted/20 rounded-lg border border-dashed border-border p-4 text-center">
                  <p className="text-xs text-muted-foreground">Unable to display group contributions.</p>
                </div>
            )}
          </div>
        </div>

        {/* C. Player-specific drivers */}
        {playerId ? (
          <PlayerExplanation player={player} />
        ) : (
          <div className="bg-card border border-border rounded-xl p-5">
            <div className="flex items-center gap-2 mb-3">
              <AlertTriangle className="w-4 h-4 text-chart-5" />
              <h3 className="font-semibold">Player-Specific Feature Drivers</h3>
            </div>
            <p className="text-xs text-muted-foreground mb-4">
              Navigate to a player detail page to see their specific risk drivers. Example shown below.
            </p>
            <ol className="space-y-2">
              {[
                { text: "minutes_median_last_5 = 90", contribution: 0.5144 },
                { text: "cup_minutes_last_14d = 90", contribution: 0.2209 },
                { text: "min_last_14d = 210", contribution: 0.1829 },
                { text: "squad_injured_count = 4", contribution: 0.1011 },
                { text: "matches_with_rest_le_4d_last_30d = 3", contribution: 0.0589 },
              ].map((r, i) => {
                const weight = Math.round(Math.min(100, Math.abs(r.contribution) * 500));
                return (
                  <li key={i} className="flex items-start gap-3">
                    <span className="w-5 h-5 rounded-full bg-primary/15 text-primary text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">
                      {i + 1}
                    </span>
                    <div className="flex-1 min-w-0">
                      <span className="text-sm text-foreground/90">{r.text}</span>
                      <span className="text-xs text-muted-foreground block">
                        Contribution: +{r.contribution.toFixed(4)}
                      </span>
                    </div>
                    <div className="w-20 h-1.5 bg-muted rounded-full overflow-hidden self-center shrink-0">
                      <div className="h-full bg-primary/60 rounded-full" style={{ width: `${weight}%` }} />
                    </div>
                  </li>
                );
              })}
            </ol>
          </div>
        )}

        {/* D. Threshold Policy */}
        <div className="bg-card border border-border rounded-xl p-6">
          <div className="flex items-center gap-2 mb-3">
            <Shield className="w-4 h-4 text-primary" />
            <h3 className="font-semibold">Threshold &amp; Monitoring Policy</h3>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
            <div className="bg-muted/30 rounded-lg p-3">
              <div className="text-xs text-muted-foreground mb-1">Core Starter Threshold</div>
              <div className="text-lg font-bold text-chart-4">{policy.core_starter_threshold ?? 0.5}</div>
            </div>
            <div className="bg-muted/30 rounded-lg p-3">
              <div className="text-xs text-muted-foreground mb-1">Rotation Player Threshold</div>
              <div className="text-lg font-bold text-chart-4">{policy.rotation_player_threshold ?? 0.5}</div>
            </div>
          </div>
          <p className="text-sm text-muted-foreground bg-muted/30 rounded-lg p-3 leading-relaxed">
            {policy.interpretation || metadata?.interpretation || "V4B is a staff-support monitoring model. A positive flag indicates that the player should be reviewed because their workload, rest pattern, competition sequence, role context, and injury context resemble situations historically associated with underperformance or managed minutes."}
          </p>
        </div>

        {/* E. Model Limitations */}
        <div className="bg-card border border-border rounded-xl p-6">
          <div className="flex items-center gap-2 mb-3">
            <Info className="w-4 h-4 text-accent" />
            <h3 className="font-semibold">Model Limitations &amp; Usage Notes</h3>
          </div>
          <ul className="space-y-2 text-sm text-muted-foreground">
            <li className="flex items-start gap-2">
              <span className="text-chart-5 mt-0.5">•</span>
              <span><strong>Correlational, not causal.</strong> The model identifies patterns associated with past underperformance or load reduction — it does not diagnose fatigue or predict injury.</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-chart-5 mt-0.5">•</span>
              <span><strong>Monitoring support only.</strong> Flags indicate "review this player", not "this player is fatigued". Always combine with GPS, wellness, and staff observation.</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-chart-5 mt-0.5">•</span>
              <span><strong>Position-normalized.</strong> Action load and minutes are compared within position groups (z-scores), so a midfielder's load is evaluated relative to other midfielders.</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-chart-5 mt-0.5">•</span>
              <span><strong>No competition features.</strong> This model variant (no_competition) excludes competition-specific features to focus on generic workload patterns.</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-chart-5 mt-0.5">•</span>
              <span>Test AUC-ROC: <strong>{metadata?.test_auc_roc?.toFixed(3) ?? "N/A"}</strong> &nbsp;|&nbsp; Test PR-AUC: <strong>{metadata?.test_pr_auc?.toFixed(3) ?? "N/A"}</strong> &nbsp;|&nbsp; Features: <strong>{metadata?.feature_count ?? "N/A"}</strong></span>
            </li>
          </ul>
        </div>

        {playerId && (
          <Link to={`/player/${playerId}`} className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors">
            <ArrowLeft className="w-4 h-4" /> Back to Player Detail
          </Link>
        )}

      </div>
    </div>
  );
}
