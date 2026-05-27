import pandas as pd
from pathlib import Path
from rapidfuzz import fuzz

rows = []
for season_dir in ["2022-2023", "2023-2024", "2024-2025"]:
    p = Path("data") / season_dir / "injuries"
    if p.exists():
        for f in sorted(p.iterdir()):
            if f.name.endswith("_injuries_days_out.csv"):
                rows.append(pd.read_csv(f))
inj = pd.concat(rows, ignore_index=True)
inj["last_name"] = inj["player_name"].str.split().str[-1].str.lower().str.strip()

print(f"Total records: {len(inj)}")
print(f"Unique player names: {inj['player_name'].nunique()}")
print(f"Teams: {inj['team_name'].nunique()}")

dup = inj.groupby("last_name")["team_name"].apply(set)
dup = dup[dup.apply(len) > 1].sort_values(key=lambda s: s.apply(len), ascending=False)
print("\nLast names on MULTIPLE teams:")
for name, teams in list(dup.items())[:20]:
    print(f"  {name}: {sorted(teams)}")

print("\nSample player names from injury data:")
for name in sorted(inj["player_name"].dropna().unique())[:30]:
    print(f"  '{name}'")

df_sample = pd.read_csv("data/2024-2025/sofascore_dynamic/fixtureiq_dynamic_master.csv", nrows=100)
print(f"\nSample player names from match data (2024-25):")
for name in sorted(df_sample["name"].dropna().unique())[:30]:
    print(f"  '{name}'")

master_last = set(df_sample["name"].str.split().str[-1].str.lower().str.strip())
injury_last = set(inj["last_name"])
unmatched = injury_last - master_last
print(f"\nInjury last names NOT in master data: {len(unmatched)}")
if unmatched:
    print("  Examples:", sorted(list(unmatched))[:15])

# Test fuzzy matching on some examples
print("\nFuzzy matching examples:")
test_pairs = [
    ("Gabriel Martinelli", "Gabriel Martinelli"),
    ("Martin Odegaard", "Martin Ødegaard"),
    ("Bukayo Saka", "Bukayo Saka"),
    ("Joao Pedro", "Joao Pedro"),
]
for inj_name, df_name in test_pairs:
    ratio = fuzz.ratio(inj_name.lower(), df_name.lower())
    partial = fuzz.partial_ratio(inj_name.lower(), df_name.lower())
    token_sort = fuzz.token_sort_ratio(inj_name.lower(), df_name.lower())
    print(f"  '{inj_name}' vs '{df_name}': ratio={ratio}, partial={partial}, token_sort={token_sort}")
