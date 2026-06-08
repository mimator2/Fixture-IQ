import sys, os, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, ".")

import pandas as pd
from fatigue_monitor.src.prediction_v6 import load_v6_artifacts, predict_v6
from fatigue_monitor.src.config import MASTER_CSV_PATH

df = pd.read_csv(MASTER_CSV_PATH, nrows=2000)
df["date"] = pd.to_datetime(df["date"])
print(f"Sample: {len(df)} rows")

m1, meta1 = load_v6_artifacts("no_competition")
m2, meta2 = load_v6_artifacts("no_rating_baseline")

v6 = predict_v6(df, m1, meta1, suffix="_v6_perf")
v6nr = predict_v6(df, m2, meta2, suffix="_v6_fatigue")

print(f"V6 Perf rows: {len(v6)}, cols: {list(v6.columns[:6])}")
print(f"V6 Fatigue rows: {len(v6nr)}, cols: {list(v6nr.columns[:6])}")
print(f"Mean perf score: {v6['risk_score_v6_perf'].mean():.4f}")
print(f"Mean fatigue score: {v6nr['risk_score_v6_fatigue'].mean():.4f}")
print("END TO END OK")
