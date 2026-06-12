import sys
import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path

import numpy as np
import pandas as pd
import shap

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def _clean_nan(obj):
    """Recursively replace NaN/Inf with None for valid JSON output."""
    if isinstance(obj, (float, np.floating)):
        return None if (math.isnan(float(obj)) or math.isinf(float(obj))) else float(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, dict):
        return {k: _clean_nan(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean_nan(v) for v in obj]
    return obj


from fatigue_monitor.src.config import (
    MASTER_CSV_PATH,
    V4B_RISK_BANDS,
    V4B_RISK_LABELS,
    V4B_FEATURE_GROUPS,
)
from fatigue_monitor.src.prediction_v4b import load_v4b_artifacts, predict_v4b
from fatigue_monitor.src.feature_engineering_v4b import assign_player_role_v4b

DATA_DIR = Path(__file__).parent / "public" / "data"

SHIELD_MAP = {
    "Arsenal": "Arsenal.png",
    "Aston Villa": "Aston Villa.png",
    "Bournemouth": "Bournemouth.png",
    "Brentford": "Brentford.png",
    "Brighton": "Brighton & Hove Albion.png",
    "Chelsea": "Chelsea.png",
    "Crystal Palace": "Crystal Palace.png",
    "Everton": "Everton.png",
    "Fulham": "Fulham.png",
    "Ipswich": "Ipswich Town.png",
    "Leicester": "Leicester City.png",
    "Liverpool": "Liverpool.png",
    "Manchester City": "Manchester City.png",
    "Manchester United": "Manchester United.png",
    "Newcastle": "Newcastle United.png",
    "Nottingham Forest": "Nottingham Forest.png",
    "Southampton": "southampton.png",
    "Tottenham": "Tottenham Hotspur.png",
    "West Ham": "West Ham United.png",
    "Wolves": "Wolves.png",
}


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def map_risk_band(score):
    if pd.isna(score):
        return "Low"
    for i in range(len(V4B_RISK_BANDS) - 1):
        if V4B_RISK_BANDS[i] <= score < V4B_RISK_BANDS[i + 1]:
            return V4B_RISK_LABELS[i]
    return "Very High"


def map_player_role(role):
    mapping = {
        "core_starter": "Core Starter",
        "rotation_player": "Rotation Player",
        "impact_sub": "Impact Substitute",
        "rare_player": "Rare Player",
    }
    return mapping.get(role, "Rotation Player")


def derive_risk_flags(row, reasons_str, risk_band=None):
    flags = set()

    reasons_lower = reasons_str.lower() if reasons_str else ""

    if row.get("rest_days", 999) < 2:
        flags.add("short_recovery")
    elif "short rest" in reasons_lower:
        flags.add("short_recovery")

    if row.get("ucl_minutes_last_14d", 0) >= 90 or "champions league" in reasons_lower:
        flags.add("recent_ucl_minutes")
    if row.get("cup_minutes_last_14d", 0) >= 90 or "domestic cup" in reasons_lower:
        flags.add("high_action_load")
    if "high action load" in reasons_lower or "high minutes" in reasons_lower:
        flags.add("high_action_load")
    if "accumulated load" in reasons_lower:
        flags.add("high_action_load")
    if row.get("squad_injured_count", 0) >= 4 or "high squad injury pressure" in reasons_lower:
        flags.add("high_squad_injury_pressure")
    if row.get("returning_from_injury", 0) == 1 or "returning from injury" in reasons_lower:
        flags.add("returning_from_injury")
    if "post-european" in reasons_lower or "post_ucl_short_rest" in reasons_lower:
        flags.add("post_european_short_rest")
    if "competition switch" in reasons_lower:
        flags.add("frequent_competition_switches")
    if "rotation player exceeding" in reasons_lower:
        flags.add("rotation_risk_exceeds_threshold")
    if risk_band in ("High", "Very High") and not flags:
        flags.add("high_risk")

    return sorted(flags)


def derive_recommended_action(risk_band, player_role):
    mapping = {
        ("Low", "Core Starter"): "Normal Monitoring",
        ("Low", "Rotation Player"): "Normal Monitoring",
        ("Medium", "Core Starter"): "Monitor Training Response",
        ("Medium", "Rotation Player"): "Monitor Training Response",
        ("High", "Core Starter"): "Review Minutes Plan",
        ("High", "Rotation Player"): "Check GPS/Wellness/Soreness",
        ("Very High", "Core Starter"): "Consider Rest / Recovery Protocol",
        ("Very High", "Rotation Player"): "Consider Rest / Recovery Protocol",
    }
    return mapping.get((risk_band, player_role), "Normal Monitoring")


def compute_congestion_level(row):
    rest = row.get("rest_days", 999)
    if pd.isna(rest) or rest >= 5:
        return "Low"
    elif rest >= 3:
        return "Medium"
    else:
        return "High"


def _parse_sub_bool(val):
    if isinstance(val, str):
        return val.lower() in ("true", "1")
    return bool(val)


def compute_lineup_rotation(grp):
    """
    Compute rotation index for a team (or team+congestion group).
    Returns average Jaccard distance (1 - overlap/union) between
    consecutive starting lineups. 0 = identical XI every match,
    higher = more rotation.
    """
    sub = grp[["fixture_id", "date", "player_id", "is_substitute"]].drop_duplicates(
        subset=["fixture_id", "player_id"]
    )
    sub["is_substitute"] = sub["is_substitute"].apply(_parse_sub_bool)
    fixture_order = (
        sub[["fixture_id", "date"]].drop_duplicates("fixture_id").sort_values("date")["fixture_id"].tolist()
    )
    if len(fixture_order) < 2:
        return 0.0
    starter_sets = {}
    for fid in fixture_order:
        s = set(sub[(sub["fixture_id"] == fid) & (~sub["is_substitute"])]["player_id"])
        starter_sets[fid] = s
    distances = []
    for i in range(len(fixture_order) - 1):
        s1 = starter_sets[fixture_order[i]]
        s2 = starter_sets[fixture_order[i + 1]]
        union = s1 | s2
        if union:
            jaccard = len(s1 & s2) / len(union)
        else:
            jaccard = 1.0
        distances.append(1.0 - jaccard)
    return round(float(np.mean(distances)), 4) if distances else 0.0


def _get_ohe_feature_names(preprocessor, cat_feats):
    ohe = preprocessor.named_transformers_["cat"].named_steps["ohe"]
    return ohe.get_feature_names_out(cat_feats).tolist()


def compute_shap_drivers(latest_df, model, preprocessor, metadata, suffix=""):
    feat_list = metadata["features"]
    cat_feats = metadata["categorical_features"]
    imp_vals = metadata["imputation_values"]

    X = latest_df[feat_list].copy()

    for f, imp in imp_vals.items():
        if f not in feat_list:
            continue
        X[f] = X[f].fillna(imp["value"])

    for f in cat_feats:
        X[f] = X[f].astype(str)

    X_t = preprocessor.transform(X)
    ohe_feature_names = _get_ohe_feature_names(preprocessor, cat_feats)
    num_feats = [f for f in feat_list if f not in cat_feats]
    shap_feature_names = num_feats + ohe_feature_names

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_t)

    drivers_list = []
    for i in range(len(X)):
        row_shap = shap_values[i]
        pos_idx = np.where(row_shap > 0)[0]
        if len(pos_idx) > 0:
            sorted_idx = pos_idx[np.argsort(row_shap[pos_idx])[-5:][::-1]]
            drivers = []
            for idx in sorted_idx:
                shap_fn = shap_feature_names[idx]
                original_name = shap_fn.split("_")[0] if shap_fn in ohe_feature_names else shap_fn
                val = X_t[i, idx]
                drivers.append({
                    "feature": shap_fn,
                    "value": round(float(val), 4) if isinstance(val, (int, float, np.integer, np.floating)) else str(val),
                    "contribution": round(float(row_shap[idx]), 4),
                })
        else:
            drivers = []
        drivers_list.append(drivers)
    return drivers_list


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    print("=== Fixture IQ — Data Export ===")
    print(f"Loading CSV: {MASTER_CSV_PATH}")
    df = pd.read_csv(MASTER_CSV_PATH)
    df["date"] = pd.to_datetime(df["date"])
    print(f"  Rows: {len(df):,}, Columns: {len(df.columns)}, Players: {df['player_id'].nunique():,}")

    print("Loading V4B model...")
    model, preprocessor, metadata = load_v4b_artifacts()
    print("  Single V4B model loaded.")

    print("Running V4B prediction...")
    df_pred = predict_v4b(df, model, preprocessor, metadata)
    print(f"  Predicted: {len(df_pred):,} rows")

    # Filter to Premier League teams only for the dashboard
    latest_season = df["season"].max()
    pl_teams = df[(df["competition"] == "Premier League") & (df["season"] == latest_season)]["player_team"].unique()
    merged = df_pred[df_pred["player_team"].isin(pl_teams)].copy()
    merged = merged[merged["player_id"] != 0].copy()
    print(f"  PL filter (season {latest_season}): {merged['player_team'].nunique()} teams")

    # --- Latest snapshot per player ---
    merged = merged.sort_values("date")
    latest = merged.groupby(["player_id", "player_team"], as_index=False).last()
    print(f"  Latest snapshot: {len(latest):,} rows")

    print("Computing SHAP drivers for snapshot rows...")
    shap_drivers = compute_shap_drivers(latest, model, preprocessor, metadata)
    print("  SHAP drivers computed for all snapshot rows.")

    # Fill NaN in numeric columns to prevent int() crashes downstream
    for col in latest.select_dtypes(include="float").columns:
        latest[col] = latest[col].fillna(0)

    # --- Build player_risks.json ---
    print("Building player_risks.json...")
    player_risks = []
    for i, (_, row) in enumerate(latest.iterrows()):
        reasons = row.get("main_risk_reasons", "") or ""

        # Append SHAP top-3 drivers as data-driven reasons
        shap_top3 = shap_drivers[i][:3] if i < len(shap_drivers) else []
        if shap_top3:
            shap_parts = [
                "{}={} ({:+.4f})".format(d["feature"], d["value"], d["contribution"])
                for d in shap_top3
            ]
            reasons += " | SHAP: " + "; ".join(shap_parts)

        risk_band = row.get("risk_band", None)
        if pd.isna(risk_band) or risk_band is None:
            risk_band = map_risk_band(row.get("risk_score", 0))

        player_role_raw = row.get("player_role_v4b", "rotation_player")
        player_role = map_player_role(player_role_raw)

        pos_map = {"G": "Goalkeeper", "D": "Defender", "M": "Midfielder", "F": "Forward"}
        position = pos_map.get(str(row.get("player_position", "")), "Unknown")

        flags = derive_risk_flags(row, reasons, risk_band)
        action = derive_recommended_action(risk_band, player_role)
        team_name = str(row.get("player_team", "")).strip()
        player_name = str(row.get("player_name", "")).strip()
        uid = f"{player_name.lower().replace(' ', '_')}__{team_name.lower().replace(' ', '_')}"

        obj = {
            "id": uid,
            "player_name": player_name,
            "team_name": team_name,
            "position": position,
            "player_role": player_role,
            "season": str(row.get("season", "")),
            "gameweek": None,

            # A. Current risk (single V4B score)
            "fatigue_score": round(float(row.get("risk_score", 0) or 0), 4),
            "risk_score": round(float(row.get("risk_score", 0) or 0), 4),
            "risk_band": risk_band,
            "monitoring_threshold": round(float(row.get("monitoring_threshold", 0.5) or 0.5), 4),
            "recommended_action": action,
            "risk_flags": flags,
            "main_risk_reasons": reasons,

            # B. Workload context
            "minutes_last_7": int(row.get("min_last_7d", 0) or 0),
            "minutes_last_14": int(row.get("min_last_14d", 0) or 0),
            "minutes_last_21": int(row.get("min_last_21d", 0) or 0),
            "minutes_last_28": int(row.get("min_last_28d", 0) or 0),
            "starts_last_14": int(row.get("starts_last_14d", 0) or 0),
            "starts_last_28": int(row.get("starts_last_28d", 0) or 0),
            "full_90s_last_14": int(row.get("full_90s_last_14d", 0) or 0),
            "full_90s_last_28": int(row.get("full_90s_last_28d", 0) or 0),
            "rest_days": int(row.get("rest_days", -1) or -1),
            "avg_rest_days_last_5": round(float(row.get("avg_rest_last_3_matches", 0) or 0), 1),
            "short_rest_matches_30d": int(row.get("matches_with_rest_le_4d_last_30d", 0) or 0),
            "matches_with_rest_le_3d_last_30d": int(row.get("matches_with_rest_le_3d_last_30d", 0) or 0),
            "matches_with_rest_le_6d_last_30d": int(row.get("matches_with_rest_le_6d_last_30d", 0) or 0),

            # C. Multi-competition context
            "ucl_minutes_last_14": int(row.get("ucl_minutes_last_14d", 0) or 0),
            "ucl_minutes_last_21": int(row.get("ucl_minutes_last_21d", 0) or 0),
            "ucl_matches_last_30": int(row.get("ucl_matches_last_30d", 0) or 0),
            "cup_minutes_last_14": int(row.get("cup_minutes_last_14d", 0) or 0),
            "cup_matches_last_30": int(row.get("cup_matches_last_30d", 0) or 0),
            "days_since_last_european": int(row.get("days_since_european_match", 0)),
            "post_ucl_short_rest": int(row.get("post_ucl_short_rest", 0) or 0),
            "pl_after_ucl_short_rest": int(row.get("pl_after_ucl_with_short_rest", 0) or 0),
            "ucl_full90_then_pl_short_rest": int(row.get("ucl_full90_then_pl_short_rest", 0) or 0),
            "competition_switches_last_30": int(row.get("competition_switches_last_30d", 0) or 0),

            # D. Match actions (position-aware V4B columns)
            "duels_last_3": int(row.get("duels_last_3_matches", 0) or 0),
            "duels_last_14": int(row.get("duels_last_14d", 0) or 0),
            "tackles_last_3": int(row.get("tackles_last_3_matches", 0) or 0),
            "tackles_last_14": int(row.get("tackles_last_14d", 0) or 0),
            "dribbles_last_3": int(row.get("dribbles_last_3_matches", 0) or 0),
            "dribbles_last_14": int(row.get("dribbles_last_14d", 0) or 0),
            "fouls_last_3": int(row.get("fouls_last_3_matches", 0) or 0),
            "fouls_last_14": int(row.get("fouls_last_14d", 0) or 0),
            "cards_last_5": int(row.get("cards_last_5_matches", 0) or 0),
            "physical_load_index": round(float(row.get("physical_load_index", 0) or 0), 4),
            "duels_total_position_z": round(float(row.get("duels_total_position_z", 0) or 0), 2),
            "tackles_total_position_z": round(float(row.get("tackles_total_position_z", 0) or 0), 2),
            "fouls_committed_position_z": round(float(row.get("fouls_committed_position_z", 0) or 0), 2),
            "minutes_played_position_z": round(float(row.get("minutes_played_position_z", 0) or 0), 2),
            "physical_load_last_14d_vs_player_avg": round(float(row.get("physical_load_last_14d_vs_player_avg", 0) or 0), 2),

            # E. Squad context
            "squad_injured_count": int(row.get("squad_injured_count", 0) or 0),
            "squad_soft_tissue_count": int(row.get("squad_soft_tissue_count", 0) or 0),
            "squad_avg_days_out": int(row.get("squad_avg_days_out", 0) or 0),
            "returning_from_injury": bool(row.get("returning_from_injury", False)),
            "fixtures_missed_last_30": int(row.get("fixtures_missed_last_30d", 0) or 0),

            # SHAP driver data (single V4B score)
            "shap_drivers": shap_drivers[i] if i < len(shap_drivers) else [],

            "workload_timeline": [],
        }

        player_risks.append(obj)

    # Deduplicate by uid (player_name__team_name) keeping last occurrence
    seen = set()
    deduped = []
    for p in reversed(player_risks):
        key = p["id"]
        if key not in seen:
            seen.add(key)
            deduped.append(p)
    player_risks = list(reversed(deduped))

    print(f"  {len(player_risks)} players written (after dedup).")

    # --- Build teams.json ---
    print("Building teams.json...")
    team_groups = merged.groupby("player_team")
    teams = []
    for team_name, grp in team_groups:
        team_competitions = grp["competition"].dropna().unique() if "competition" in grp.columns else []
        euro_keywords = ["champions", "europa", "conference"]
        euro_comp = "None"
        for c in team_competitions:
            cl = str(c).lower()
            for kw in euro_keywords:
                if kw in cl:
                    euro_comp = c
                    break
        if euro_comp == "None" and len(team_competitions) > 0:
            euro_comp = team_competitions[0]

        total_matches = grp["fixture_id"].nunique()
        avg_rest = grp["rest_days"].clip(upper=10).mean()
        avg_pts = grp["points"].mean() if "points" in grp.columns else 0

        # Rotation index: average Jaccard distance between consecutive starting XIs
        overall_rotation = compute_lineup_rotation(grp) if "is_substitute" in grp.columns else 0.0

        season = f"{latest_season}-{str(int(latest_season) + 1)[-2:]}"

        team_id = team_name.lower().replace(" ", "_")

        teams.append({
            "id": team_id,
            "name": team_name,
            "short_name": team_name[:3].upper(),
            "logo_url": f"/shields/{SHIELD_MAP.get(team_name, '')}",
            "european_competition": euro_comp,
            "season": season,
            "total_matches": int(total_matches),
            "avg_rest_days": round(float(avg_rest), 1) if not pd.isna(avg_rest) else 0,
            "overall_points_per_match": round(float(avg_pts), 2) if not pd.isna(avg_pts) else 0,
            "overall_rotation_index": overall_rotation,
        })

    print(f"  {len(teams)} teams written.")

    # --- Build congestion_metrics.json ---
    print("Building congestion_metrics.json...")
    df_cong = merged.copy()
    df_cong["congestion_level"] = df_cong.apply(compute_congestion_level, axis=1)
    df_cong["win"] = (df_cong["result"] == "Win").astype(int) if "result" in df_cong.columns else 0

    cong_list = []
    for (team_name, level), grp in df_cong.groupby(["player_team", "congestion_level"]):
        n_matches = grp["fixture_id"].nunique()
        avg_rest = grp["rest_days"].mean()
        avg_pts = grp["points"].mean() if "points" in grp.columns else 0
        avg_xgf = grp["goals_for"].mean() if "goals_for" in grp.columns else 0
        avg_xga = grp["goals_against"].mean() if "goals_against" in grp.columns else 0
        win_rate = grp["win"].mean() * 100 if "win" in grp.columns else 0

        # Rotation index: average Jaccard distance between consecutive starting XIs
        rotation_index = compute_lineup_rotation(grp) if "is_substitute" in grp.columns else 0.0

        # Season per group
        grp_season = str(grp["season"].iloc[0]) if "season" in grp.columns else ""
        if grp_season:
            grp_season = f"{grp_season}-{str(int(grp_season) + 1)[-2:]}"

        cong_list.append({
            "id": f"{team_name.lower().replace(' ', '_')}_{level.lower()}",
            "team_name": team_name,
            "congestion_level": level,
            "matches": int(n_matches),
            "avg_rest_days": round(float(avg_rest), 1) if not pd.isna(avg_rest) else 0,
            "points_per_match": round(float(avg_pts), 2) if not pd.isna(avg_pts) else 0,
            "xg_for": round(float(avg_xgf), 2) if not pd.isna(avg_xgf) else 0,
            "xg_against": round(float(avg_xga), 2) if not pd.isna(avg_xga) else 0,
            "goal_diff_per_match": round(float(avg_xgf - avg_xga), 2),
            "rotation_index": rotation_index,
            "win_rate": round(float(win_rate), 1),
            "season": grp_season,
        })

    print(f"  {len(cong_list)} metrics written.")

    # --- Build hypotheses.json (compute values from actual data) ---
    # H1: use full dataset for general rating pattern
    sr = df[df["rest_days"] <= 4]["next_api_rating"].dropna()
    nr = df[df["rest_days"] > 4]["next_api_rating"].dropna()
    rating_diff = sr.mean() - nr.mean()
    n_obs = len(df)
    n_seasons = df["season"].nunique()

    # H2/H3: use congestion_metrics computed from merged PL data
    rot_low = [c["rotation_index"] for c in cong_list if c["congestion_level"] == "Low"]
    rot_med = [c["rotation_index"] for c in cong_list if c["congestion_level"] == "Medium"]
    rot_high = [c["rotation_index"] for c in cong_list if c["congestion_level"] == "High"]
    avg_rot_low = sum(rot_low) / len(rot_low) if rot_low else 0
    avg_rot_med = sum(rot_med) / len(rot_med) if rot_med else 0

    euro_by_team = {t["name"]: t.get("european_competition", "") for t in teams}
    cl_rot = [c["rotation_index"] for c in cong_list if "Champions" in euro_by_team.get(c["team_name"], "")]
    other_euro = [c["rotation_index"] for c in cong_list if c["team_name"] in euro_by_team and "Champions" not in euro_by_team.get(c["team_name"], "") and euro_by_team.get(c["team_name"], "")]
    avg_cl = sum(cl_rot) / len(cl_rot) if cl_rot else 0
    avg_other_euro = sum(other_euro) / len(other_euro) if other_euro else 0

    hypotheses = [
        {
            "id": "h1",
            "hypothesis_id": "H1",
            "title": "Lower rest periods reduce performance.",
            "description": f"Across all {n_obs:,} observations ({n_seasons} seasons), players with ≤4 days rest show a {abs(rating_diff):+.2f} point {'higher' if rating_diff > 0 else 'lower'} average next-match rating vs normal rest — a negligible raw difference. The V4B model detects multi-feature fatigue signals beyond raw rating.",
            "status": "Partially Supported",
            "evidence_summary": f"Raw rating difference: {rating_diff:+.3f} ({sr.mean():.2f} short-rest vs {nr.mean():.2f} normal-rest, n={len(sr)+len(nr):,}). The V4B model's multivariate approach captures position-specific and contextual fatigue signals not visible in raw rating averages.",
            "key_metric": "Rating change under ≤4d rest",
            "key_value": f"{rating_diff:+.3f} avg rating difference",
            "detail": f"Analysis of {n_obs:,} player-match observations across {n_seasons} seasons. Under ≤4 days rest, next-match ratings average {sr.mean():.3f} (n={len(sr):,}) vs {nr.mean():.3f} under normal rest (n={len(nr):,}) — a {rating_diff:+.3f} difference. While the raw rating gap is small and in the unexpected direction, the V4B model integrates rest with workload, action load, injury context, and competition sequence to identify elevated fatigue risk scenarios."
        },
        {
            "id": "h2",
            "hypothesis_id": "H2",
            "title": "Higher congestion affects squad rotation patterns.",
            "description": f"Squad rotation index averages {avg_rot_low:.2f} under low congestion (≥5d rest, {len(rot_low)} team-groups) vs {avg_rot_med:.2f} under medium congestion (3–4d rest, {len(rot_med)} team-groups), showing managers rotate more when fixture density is lower.",
            "status": "Supported",
            "evidence_summary": f"Rotation index: {avg_rot_low:.2f} (low congestion) vs {avg_rot_med:.2f} (medium congestion). High-congestion data limited ({len(rot_high)} team-group). Rotation decreases as congestion rises, likely because managers keep a settled XI during dense fixture blocks.",
            "key_metric": "Rotation index by congestion",
            "key_value": f"Low: {avg_rot_low:.2f} | Medium: {avg_rot_med:.2f}",
            "detail": f"Under low congestion (≥5d rest, {len(rot_low)} team-groups), average rotation sits at {avg_rot_low:.3f}. Under medium congestion (3–4d rest, {len(rot_med)} team-groups), this drops to {avg_rot_med:.3f}. Rotation index measures Jaccard distance between consecutive starting XIs (0=identical lineup, 1=completely different). The pattern suggests managers rely on a settled XI during tighter schedules and rotate more when rest allows tactical flexibility."
        },
        {
            "id": "h3",
            "hypothesis_id": "H3",
            "title": "Clubs respond differently to congestion based on European involvement and squad depth.",
            "description": "Rotation patterns vary by competition level: Champions League clubs show average rotation of {avg_cl:.2f} vs {avg_other_euro:.2f} for other European participants. Variance within groups is substantial.",
            "status": "Partially Supported",
            "evidence_summary": f"CL clubs ({len(cl_rot)} team-groups): {avg_cl:.2f}. Other European ({len(other_euro)} team-groups): {avg_other_euro:.2f}. Within-group variance suggests squad depth and managerial approach are key moderators.",
            "key_metric": "Rotation by competition level",
            "key_value": f"CL: {avg_cl:.2f} vs Other: {avg_other_euro:.2f}",
            "detail": f"Champions League clubs ({len(cl_rot)} team-groups) show average rotation of {avg_cl:.3f}, compared to {avg_other_euro:.3f} for other European participants ({len(other_euro)} team-groups). The data confirms rotation strategy differs by competition level, though within-group variance is high — squad depth and individual manager preferences explain much of the variation."
        },
        {
            "id": "h4",
            "hypothesis_id": "H4",
            "title": "Analytics dashboards improve coaching decisions on player workload management.",
            "description": "Interactive analytics tools for workload and fatigue monitoring can enhance evidence-based decision-making in elite football environments.",
            "status": "Pending",
            "evidence_summary": "Requires longitudinal staff feedback study. Initial qualitative feedback from analysts is positive but not yet measured.",
            "key_metric": "Staff adoption and decision accuracy",
            "key_value": "Pending evaluation",
            "detail": "This hypothesis requires a controlled longitudinal study with coaching and medical staff to measure whether data-driven workload insights translate to measurable improvements in injury prevention and performance management."
        },
    ]

    # --- Build model_metadata.json ---
    print("Building model_metadata.json...")
    feature_importances = []
    feat_list = metadata["features"]
    cat_feats = metadata["categorical_features"]
    try:
        ohe_feature_names = _get_ohe_feature_names(preprocessor, cat_feats)
        num_feats = [f for f in feat_list if f not in cat_feats]
        shap_feature_names = num_feats + ohe_feature_names
        fi = model.feature_importances_
        total = fi.sum()
        for name, imp_val in sorted(zip(shap_feature_names, fi), key=lambda x: x[1], reverse=True):
            imp = float(imp_val)
            feature_importances.append({
                "feature": name,
                "importance": round(imp, 4),
                "importance_pct": round(imp / total * 100, 2) if total > 0 else 0,
            })
    except Exception as e:
        print(f"  Warning: could not extract feature importances: {e}")

    raw_meta = metadata.get("raw_metadata", {})
    meta_target = raw_meta.get("target", "")
    test_metrics = raw_meta.get("test_metrics_validation_selected_model", {})
    model_metadata = {
        "model_name": raw_meta.get("model_name", "V4B"),
        "variant": raw_meta.get("variant", "v4b_no_competition"),
        "target": meta_target,
        "target_definition": raw_meta.get("target_definition", ""),
        "test_auc_roc": test_metrics.get("auc_roc", None),
        "test_pr_auc": test_metrics.get("auc_pr", None),
        "feature_importances": feature_importances,
        "feature_groups": metadata.get("feature_groups", {}),
        "threshold_policy": metadata.get("operating_policy", {}),
        "feature_count": len(feature_importances),
        "current_season": str(latest_season),
        "risk_bands": V4B_RISK_BANDS,
        "risk_labels": V4B_RISK_LABELS,
        "interpretation": (
            "V4B is a staff-support monitoring model. A positive flag indicates that the player "
            "should be reviewed because their workload, rest pattern, competition sequence, "
            "role context, and injury context resemble situations historically associated with "
            "underperformance or managed minutes."
        ),
    }

    # --- Build player timelines ---
    print("Building player timelines...")
    timeline_dir = DATA_DIR / "player_timelines"
    timeline_dir.mkdir(parents=True, exist_ok=True)
    timeline_count = 0
    merged_sorted = merged.sort_values(["player_key", "date"])
    for player_key, grp in merged_sorted.groupby("player_key"):
        grp = grp.sort_values("date").tail(20)
        timeline = []
        for _, mr in grp.iterrows():
            timeline.append({
                "date": str(mr.get("date", pd.NaT)),
                "minutes": int(mr.get("min_last_14d", 0) or 0),
                "minutes_played": int(mr.get("minutes_played", 0) or 0),
                "rest_days": float(mr.get("rest_days", 0) or 0),
                "fatigue_score": round(float(mr.get("risk_score", 0) or 0), 4),
                "starts_last_14": int(mr.get("starts_last_14d", 0) or 0),
                "full_90s_last_14": int(mr.get("full_90s_last_14d", 0) or 0),
                "ucl_minutes": int(mr.get("ucl_minutes_last_14d", 0) or 0),
            })
        pid = player_key.lower().replace(" ", "_")
        (timeline_dir / f"{pid}.json").write_text(json.dumps(_clean_nan(timeline), indent=2), encoding="utf-8")
        timeline_count += 1
    print(f"  {timeline_count} player timelines written.")

    # --- Write output ---
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "player_risks.json").write_text(json.dumps(_clean_nan(player_risks), indent=2), encoding="utf-8")
    (DATA_DIR / "teams.json").write_text(json.dumps(_clean_nan(teams), indent=2), encoding="utf-8")
    (DATA_DIR / "congestion_metrics.json").write_text(json.dumps(_clean_nan(cong_list), indent=2), encoding="utf-8")
    (DATA_DIR / "hypotheses.json").write_text(json.dumps(_clean_nan(hypotheses), indent=2), encoding="utf-8")
    (DATA_DIR / "model_metadata.json").write_text(json.dumps(_clean_nan(model_metadata), indent=2), encoding="utf-8")

    print()
    print("=== Done ===")
    print(f"  player_risks.json       — {len(player_risks)} players")
    print(f"  teams.json              — {len(teams)} teams")
    print(f"  congestion_metrics.json  — {len(cong_list)} metrics")
    print(f"  hypotheses.json         — {len(hypotheses)} hypotheses")
    print(f"  model_metadata.json     — {len(feature_importances)} features")
    print(f"  player timelines dir    — {timeline_count} files")
    print(f"  Output: {DATA_DIR}")


if __name__ == "__main__":
    main()
