import json

# Paste the entire code block I gave you inside the triple quotes below
notebook_data = """
{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# FixtureIQ — Statistical Report & Data Quality Exploration\n",
    "\n",
    "## Analytical Intent\n",
    "This notebook bypasses functional data manipulation pipeline steps to deliver a pure **Data Quality Report Analysis**. \n",
    "We investigate structural features across your datasets to isolate:\n",
    "1. **Data Types & Types Mismatch:** Uncovering text vs numeric casting anomalies (e.g., dates treated as strings).\n",
    "2. **Null Values & Empty Arrays:** Quantifying actual `NaN` presence versus contextual 'Structural Zeroes' (e.g., unused substitutes).\n",
    "3. **Outliers & Extremes:** Finding mathematical anomalies, heavy right-skews (e.g., major injury durations), and Per-90 inflation metrics."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "import pandas as pd\n",
    "import numpy as np\n",
    "import matplotlib.pyplot as plt\n",
    "import seaborn as sns\n",
    "import glob\n",
    "from pathlib import Path\n",
    "import warnings\n",
    "warnings.filterwarnings('ignore')\n",
    "\n",
    "sns.set_style('whitegrid')\n",
    "plt.rcParams['figure.figsize'] = (15, 5)\n",
    "\n",
    "# Set relative or absolute base path tracing\n",
    "BASE = Path('__file__').resolve().parent if '__file__' in locals() else Path('..')\n",
    "print(f\"Project root evaluated: {BASE.resolve()}\")"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "---\n",
    "## 1. High-Frequency Per-Match Logs: SofaScore Dynamic\n",
    "Analyzing column data density, tracking variables, and checking for anomalies caused by short-stint substitute appearances."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "dynamic_paths = list(BASE.glob('Data/*/sofascore_dynamic/fixtureiq_dynamic_analytics_clean.csv'))\n",
    "\n",
    "if dynamic_paths:\n",
    "    print(f\"--- Loading Dynamic Logs for Profiling ({len(dynamic_paths)} seasons) ---\")\n",
    "    dyn_df = pd.concat([pd.read_csv(p) for p in dynamic_paths], ignore_index=True)\n",
    "    \n",
    "    print(\"\\n[1.1 SCHEMA INFO & DATA TYPES]\")\n",
    "    print(dyn_df.info())\n",
    "    \n",
    "    print(\"\\n[1.2 ACCURATE MISSING VALUE PROFILING]\")\n",
    "    null_counts = dyn_df.isnull().sum()\n",
    "    if null_counts.sum() == 0:\n",
    "        print(\"No true missing (NaN) values present. System uses complete tracking blocks.\")\n",
    "    else:\n",
    "        print(null_counts[null_counts > 0])\n",
    "        \n",
    "    print(\"\\n[1.3 IDENTIFYING STRUCTURAL ZEROES (Unused Substitutes vs Missing Data)]\")\n",
    "    if 'minutesPlayed' in dyn_df.columns:\n",
    "        unused_subs = (dyn_df['minutesPlayed'] == 0).sum()\n",
    "        print(f\"Rows where Minutes Played == 0 (Bench players with 0-stats instead of Nulls): {unused_subs:,} ({unused_subs/len(dyn_df)*100:.2f}% of data)\")\n",
    "    \n",
    "    print(\"\\n[1.4 STATISTICAL OUTLIER ANALYSIS]\")\n",
    "    # Focus heavily on numeric tracking metrics prone to skews\n",
    "    numeric_cols = dyn_df.select_dtypes(include=[np.number]).columns\n",
    "    core_metrics = [c for c in ['minutesPlayed', 'acwr_ratio', 'rest_days', 'sofascore_rating'] if c in numeric_cols]\n",
    "    \n",
    "    if core_metrics:\n",
    "        desc = dyn_df[core_metrics].describe(percentiles=[0.01, 0.25, 0.50, 0.75, 0.99])\n",
    "        print(desc)\n",
    "        \n",
    "        print(\"\\n[1.5 DISTRIBUTION DISTORTION (Skewness Summary)]\")\n",
    "        for col in core_metrics:\n",
    "            print(f\"  {col:<20} Skewness Score: {dyn_df[col].skew():.3f} (Values > 1 indicate heavy right-hand outlier tails)\")\n",
    "else:\n",
    "    print(\"❌ SofaScore Dynamic files not found for profiling.\")"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "---\n",
    "## 2. FBref Consolidated Per-Match Masters\n",
    "Analyzing the structure of combined match logs (`master_player_stats.csv`) to check for statistical skews caused by short appearance times."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "fbref_masters = list(BASE.glob('Data/*/fbref/*/master_player_stats.csv'))\n",
    "\n",
    "if fbref_masters:\n",
    "    print(f\"--- Profiling FBref Consolidated Match Masters ({len(fbref_masters)} teams found) ---\")\n",
    "    fbref_df = pd.concat([pd.read_csv(p) for p in fbref_masters], ignore_index=True)\n",
    "    \n",
    "    print(\"\\n[2.1 DATA SHEET DIMENSIONS & DATATYPES]\")\n",
    "    print(fbref_df.info())\n",
    "    \n",
    "    print(\"\\n[2.2 DETECTION OF OVERAL COLUMN HOLES / VALUE GAPS]\")\n",
    "    fb_nulls = fbref_df.isnull().sum()\n",
    "    if fb_nulls.sum() > 0:\n",
    "        print(fb_nulls[fb_nulls > 0].sort_values(ascending=False).head(15))\n",
    "    else:\n",
    "        print(\"Zero true blanks detected in integrated rows.\")\n",
    "        \n",
    "    print(\"\\n[2.3 THE RATE-METRIC OUTLIER RISK (Short Minutes Played Exception)]\")\n",
    "    min_col = [c for c in fbref_df.columns if 'min' in c.lower()]\n",
    "    if min_col:\n",
    "        m_col = min_col[0]\n",
    "        short_stints = fbref_df[fbref_df[m_col] < 15]\n",
    "        print(f\"Data points where active time is under 15 minutes: {len(short_stints):,} rows ({len(short_stints)/len(fbref_df)*100:.2f}% of records)\")\n",
    "        print(\"⚠️ Caution: Per-90 scaling metrics computed from these rows will display massive artificial spikes.\")\n",
    "else:\n",
    "    print(\"❌ Consolidated master_player_stats files not found.\")"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "---\n",
    "## 3. FBref Seasonal Compendiums & Overview Files\n",
    "Profiling `*_players_all_competitions.csv` across teams to identify gaps in seasonal coverage and check for missing data in specific tournaments."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "compendium_paths = list(BASE.glob('Data/*/fbref/*/*_players_all_competitions.csv'))\n",
    "\n",
    "if compendium_paths:\n",
    "    print(f\"--- Profiling Seasonal Squad Compendiums ({len(compendium_paths)} files detected) ---\")\n",
    "    comp_df = pd.concat([pd.read_csv(p) for p in compendium_paths], ignore_index=True)\n",
    "    \n",
    "    print(\"\\n[3.1 MACRO MATRIX SUMMARY]\")\n",
    "    print(f\"Total squad listings integrated: {comp_df.shape[0]:,} records across {comp_df.shape[1]} descriptors.\")\n",
    "    \n",
    "    print(\"\\n[3.2 STRUCTURAL GAP PROFILING (Cross-Competition Gaps)]\")\n",
    "    gaps = comp_df.isnull().sum()\n",
    "    valuable_gaps = gaps[gaps > 0].sort_values(ascending=False)\n",
    "    if not valuable_gaps.empty:\n",
    "        print(\"Top columns with empty values (occurs when squads do not record minutes in monitored tournaments):\")\n",
    "        print(valuable_gaps.head(10))\n",
    "    else:\n",
    "        print(\"Symmetric distribution matrix: No missing tournament metric cells discovered.\")\n",
    "else:\n",
    "    print(\"❌ Seasonal overview compendiums (*_players_all_competitions.csv) not found.\")"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "---\n",
    "## 4. Target Variables Analysis: Injury Logs\n",
    "Evaluating the mathematical profile of injury lengths. We look for right-skewed tail distributions caused by long-term ligament injuries or severe medical layouts."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "injury_paths = list(BASE.glob('Data/*/injuries/*_injuries_days_out.csv'))\n",
    "\n",
    "if injury_paths:\n",
    "    print(f\"--- Analyzing Ground Truth Target Injury Metrics ({len(injury_paths)} data sets loaded) ---\")\n",
    "    inj_df = pd.concat([pd.read_csv(p) for p in injury_paths], ignore_index=True)\n",
    "    \n",
    "    print(\"\\n[4.1 STRUCTURAL TYPE STABILITY]\")\n",
    "    print(inj_df.info())\n",
    "    \n",
    "    print(\"\\n[4.2 ANALYSIS OF ACTIVE LABELS (Open-ended Timelines)]\")\n",
    "    # Active cases contain empty values for recovery or return timelines\n",
    "    return_cols = [c for c in ['return_date', 'expected_return'] if c in inj_df.columns]\n",
    "    for col in return_cols:\n",
    "        missing_returns = inj_df[col].isnull().sum()\n",
    "        print(f\"  Column '{col}' holds {missing_returns} blanks. (These represent active/ongoing injuries during data scraping).\")\n",
    "        \n",
    "    print(\"\\n[4.3 MEDICAL PROFILE RANGE EXPANSION (Days Out Distribution Metrics)]\")\n",
    "    days_col = [c for c in ['days_out', 'length', 'duration'] if c in inj_df.columns]\n",
    "    if days_col:\n",
    "        d_col = days_col[0]\n",
    "        # Enforce clean numerical coercion for reliable statistics\n",
    "        inj_df[d_col] = pd.to_numeric(inj_df[d_col], errors='coerce')\n",
    "        \n",
    "        print(inj_df[d_col].describe(percentiles=[0.25, 0.50, 0.75, 0.90, 0.95, 0.99]))\n",
    "        \n",
    "        skewness = inj_df[d_col].skew()\n",
    "        print(f\"\\nTarget Duration Skewness metric: {skewness:.3f}\")\n",
    "        if skewness > 2.0:\n",
    "            print(\"🚨 Critical Outlier Signal: The distribution features a heavy right-hand tail.\")\n",
    "            print(\"   While most instances are brief tweaks (< 21 days), rare long-term injuries (e.g., ACL tears > 200 days) distort the mean values.\")\n",
    "            \n",
    "        # Render distribution visualization\n",
    "        plt.figure(figsize=(12, 4))\n",
    "        sns.boxplot(x=inj_df[d_col], color='salmon')\n",
    "        plt.title(f'Structural Outlier Identification Boxplot: {d_col}')\n",
    "        plt.xlabel('Number of Days Absent')\n",
    "        plt.show()\n",
    "else:\n",
    "    print(\"❌ Historical Injury log paths could not be loaded for profiling.\")"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "name": "python",
   "version": "3.10.0"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}
"""

# Save it as an official Jupyter Notebook file
with open("notebooks/data_exploration_new.ipynb", "w", encoding="utf-8") as f:
    f.write(notebook_data.strip())

print("✅ Your new notebook 'notebooks/data_exploration_new.ipynb' has been created successfully!")