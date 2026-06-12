# Fixture IQ

## 🎯 Project Overview

**Fixture IQ** is a data-driven analytical framework designed to quantify fixture congestion in elite football and evaluate its relationship with competitive performance and squad rotation. The project covers Premier League clubs competing in European competitions across the 2022–2025 seasons (68,700+ player-match observations).

---

## 📌 Origin & Motivation

### The Business Challenge

Professional football has become increasingly demanding, with clubs competing simultaneously in:
- Domestic leagues (Premier League)
- Domestic cups (FA Cup, EFL Cup, Community Shield)
- International tournaments (UEFA Champions League)

This creates periods where teams must play multiple games within short intervals—a phenomenon known as **fixture congestion**. For clubs involved in European competitions, this is not only a sporting challenge but also a business and performance-management problem.

### Why This Matters

Fixture congestion is one of the most discussed practical challenges in elite football, yet it is often debated through opinion rather than structured evidence. Understanding and managing congestion is critical because:

- **Performance Impact**: Tight schedules can reduce competitive output and affect league position
- **Player Management**: Creates complex decisions about rotation, rest, and recovery
- **Financial Consequences**: Performance directly affects prize money, European qualification, broadcasting revenue, and club prestige
- **Resource Optimization**: Clubs invest heavily in analytics to optimize squad management

---

## 💡 Business Justification

The economic interest in this topic is strong because competitive performance in elite football has direct financial consequences:

- **Prize Money**: Position in league and European competition outcomes
- **European Qualification**: Access to lucrative Champions League revenue
- **Broadcasting & Sponsorship**: Performance visibility affects commercial value
- **Player Market Value**: Results influence transfer valuations
- **Long-term Reputation**: Sustained performance builds club brand equity

Even small performance differences can translate into significant financial consequences. A drop in league position or European elimination directly affects revenue, while advanced analytics capabilities have become essential for competitive clubs.

---

## 🔬 Main Objective

**Develop a data-driven framework that quantifies fixture congestion and evaluates its relationship with competitive performance and squad rotation in Premier League clubs competing in European competitions, using an XGBoost machine learning model.**

### Specific Objectives

1. **Data Integration**: Collect and integrate match, lineup, minutes, and performance data from public football sources (API-Football, FBref) into a structured dataset via automated extraction pipelines.

2. **Congestion Indicators**: Define and compute player-level workload metrics:
   - Days of rest between matches
   - Number of matches in rolling time windows (7, 14, 21, 28 days)
   - Domestic/European fixture sequences and transitions
   - ACWR (acute-to-chronic workload ratio)
   - Position-adjusted z-scores for minutes and action load

3. **Exploratory Analysis**: Analyze team-level and player-level patterns:
   - Rest-period distributions and congestion categories
   - Points per match and goal difference under high/moderate/normal rest
   - European "hangover" effect on subsequent Premier League performance
   - Squad rotation patterns and Jaccard-based rotation indices
   - Injury-availability contextualisation

4. **Machine Learning Modelling**:
   - **XGBoost V4B** (`fatigue_monitor/models/xgboost_v4b/`): Active fatigue-performance risk model. 75 features: workload windows, competition sequence, action load, injury context, position-adjusted z-scores. AUC-ROC 0.634, AUC-PR 0.422.
   - **CatBoost V6** (`models/CatBoostClassifier/CatBoost.ipynb`): Complementary role-adjusted performance-risk model (legacy — not used by dashboard).
   - The model predicts binary player-match risk labels for staff-support monitoring, with role-specific alert thresholds.

5. **Dashboard Development**: A React + Vite frontend (`dashboard/`) that transforms model outputs into interpretable visual intelligence: risk badges, SHAP driver explanations, workload timelines, team congestion charts, and feature group contribution breakdowns.

---

## 📊 Core Hypotheses

- **H1**: Lower rest periods reduce performance. *Status: Not Supported — short-rest groups (≤3d) average slightly higher next-match ratings than normal-rest groups in both scorable (minutes ≥45) and full-population views, indicating simple rest heuristics do not predict fatigue.*
- **H2**: Fixture congestion influences squad rotation patterns. *Status: Supported — rotation index 0.625 (low) vs 0.558 (medium). Managers keep a more settled XI during dense fixture blocks.*
- **H3**: Clubs respond differently to congestion based on European involvement and squad depth. *Status: Partially Supported — Champions League clubs rotate 0.557 vs non-CL clubs 0.591; within-group variance is high.*
- **H4**: A data-driven dashboard can help staff identify workload risk and support performance management decisions. *Status: Pending — requires longitudinal staff feedback study.*

---

## 🔄 Analytical Workflow

### Phase 1: Data Foundation
- Load and standardize match data from multiple teams
- Create unified match calendar across all competitions
- Extract temporal patterns and fixture density metrics

### Phase 2: Dataset Construction
- Calculate rest periods between matches
- Define rolling match counts (7, 14, 21-day windows)
- Create congestion categories (low/medium/high)
- Flag European competition context

### Phase 3: Performance Analysis
- Analyze impact of rest periods on goals scored
- Evaluate European competition "hangover" effect
- Correlate rolling congestion with PPM (points per match) and goal difference
- Compare aggregate vs. team-specific responses

### Phase 4: Strategic Insights
- Identify most damaging fixture transitions
- Evaluate team-specific resilience under congestion
- Quantify rotation patterns and squad utilization
- Generate actionable recommendations

---

## 📈 Key Findings (2022–2025)

Based on analysis of the full Premier League dataset (20 clubs, 68,700+ player-match observations):

- **V4B Model Performance**: AUC-ROC 0.634, AUC-PR 0.422 (1.38× baseline). Top drivers: position-normalised minutes, physical load vs season average, full-90 exposure, match frequency, rest patterns.
- **Rotation Patterns**: Average rotation index 0.625 under low congestion vs 0.558 under medium congestion — managers keep a more settled XI during tighter schedules.
- **CL vs non-CL**: Champions League clubs rotate 0.557 vs non-CL clubs 0.591; within-group variance is substantial.
- **Feature Profile**: The V4B model's top features are interpretable workload/rest/recovery variables — minutes, starts, full-90s, rest days, UCL burden, physical action load.
- **Model Limitations**: The model is correlational, not causal. It flags players for staff review, not automatic rest decisions. No GPS, wellness, or medical data is included.

---

## 🛠️ Technologies & Libraries

- **Python 3.10+**: pandas, numpy, scikit-learn, xgboost, shap, joblib
- **Data extraction**: API-Football (REST), FBref (Selenium), SofaScore
- **Machine learning**: XGBoost (V4B), SHAP for interpretability
- **Dashboard**: React 18, Vite 6, Tailwind CSS, shadcn/ui, Recharts, TanStack Query
- **Notebooks**: Jupyter
- **Version control**: Git/GitHub

---

## 🚀 Launch dashboard

```bash
cd dashboard
pip install -r ..\requirements.txt
python export_data.py    # ~2 min: CSV → XGBoost V4B inference → public/data/*.json
npm install              # first time only
npm run dev              # http://localhost:5173
```

---

## 📁 Repository Structure

| Directory | Purpose |
|-----------|---------|
| `Data/` | Master CSV (68k+ rows) and raw extraction outputs (gitignored) |
| `Data_Extraction/` | Pipelines for API-Football, FBref, SofaScore |
| `models/` | Training notebooks for XGBoost V4B + CatBoost V6 (legacy) |
| `fatigue_monitor/` | Active inference pipeline, feature engineering, model artifacts |
| `dashboard/` | React + Vite frontend and `export_data.py` batch job |
| `thesis_memory/` | Thesis draft storage |

See each directory's README.md for detailed documentation.

---

##  Contributing

This project welcomes:
- Additional team data
- Alternative data sources
- Enhanced visualization approaches
- Advanced statistical models
- Performance improvements


---

**Last Updated**: Jun 2026  
**Status**: Active Development
