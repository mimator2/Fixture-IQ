# Fixture IQ

## 🎯 Project Overview

**Fixture IQ** is a data-driven analytical framework designed to quantify fixture congestion in elite football and evaluate its relationship with competitive performance and squad rotation. The project focuses on Premier League clubs competing in European competitions during the 2024-2025 season.

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

**Develop a data-driven framework that quantifies fixture congestion and evaluates its relationship with competitive performance and squad rotation in Premier League clubs competing in European competitions.**

### Specific Objectives

1. **Data Integration**: Collect and integrate match, lineup, minutes, and performance data from public football sources into a structured dataset

2. **Congestion Indicators**: Define and compute metrics such as:
   - Days of rest between matches
   - Number of matches in rolling time windows (7, 14, 21 days)
   - Domestic/European fixture sequences and transitions

3. **Performance Analysis**: Analyze relationships between congestion and:
   - Points earned and match results
   - Goal difference
   - Expected goals (xG) and other advanced metrics
   - Win rates under different scheduling conditions

4. **Rotation Analysis**: Measure changes in:
   - Starting lineup composition
   - Player-minute distribution
   - Squad usage patterns across congestion levels
   - Team-specific rotation strategies

5. **Comparative Insights**: Identify:
   - Whether highly congested periods correlate with lower performance
   - How different teams respond to similar scheduling pressure
   - Which fixture transitions are most damaging

6. **Decision Support**: Design a prototype dashboard and analytical framework to support:
   - Performance analysts
   - Coaching staff
   - Technical directors
   - Strategic planning

---

## 📊 Core Hypotheses

- **H1**: Lower rest periods and higher match density are associated with lower competitive performance
- **H2**: Higher fixture congestion is associated with greater squad rotation
- **H3**: Clubs show different rotation responses under congested conditions
- **H4**: A data-driven dashboard can effectively identify congestion windows and support performance analysis

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

## 📈 Key Findings (2024-25 Season)

Based on analysis of Arsenal, Aston Villa, Liverpool, and Manchester City:

- **Congestion Impact**: Teams show measurable performance decline under fixture density
- **Defensive Vulnerability**: Goal-against rate increases more than offensive decline during congestion
- **European Hangover**: Post-Champions League matches show -13% PPM reduction
- **Team Variation**: Response to congestion varies significantly (e.g., Liverpool +20% vs Manchester City -23% under pressure)
- **Strategic Transitions**: PL-to-CL transitions are most damaging; CL-to-PL transitions show recovery

---

## 🛠️ Technologies & Libraries

- **Python 3.10+**
- **Data Analysis**: pandas, numpy
- **Visualization**: matplotlib, seaborn, PIL
- **Notebooks**: Jupyter
- **Version Control**: Git/GitHub

---

## 🚀 Usage

1. **Review Data Sources**: See [Data.md](Data.md) for source descriptions and collection methods
2. **Run Analysis**: Execute `01_Match_Calendar_and_Workload_Analysis.ipynb` sequentially
3. **Interpret Results**: Follow markdown section headers for analytical flow and findings
4. **Generate Insights**: Use visualizations and tables to inform squad management decisions

---

## 📝 Project Timeline

- **Data Collection**: 2024-25 season (August 2024 - May 2025)
- **Analysis Phase**: Current
- **Dashboard Development**: In progress
- **Recommendations**: Ongoing

---

## 🤝 Contributing

This project welcomes:
- Additional team data
- Alternative data sources
- Enhanced visualization approaches
- Advanced statistical models
- Performance improvements

---

## 📧 Contact & Inquiries

For questions, suggestions, or collaboration opportunities, please open an issue or contact the project maintainer.



---

**Last Updated**: May 2026  
**Status**: Active Development
