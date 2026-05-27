"""
FixtureIQ — Fatigue Risk Dashboard
====================================
Streamlit web app showcasing the XGBoost fatigue/injury risk model.

Run with:
    streamlit run src/visualization/dashboard.py
"""

import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import json
import pickle

import xgboost as xgb
from sklearn.metrics import (
    roc_auc_score, average_precision_score,
    precision_recall_curve, roc_curve,
    classification_report, confusion_matrix
)

from src.config.paths import data_dir, model_dir, results_dir

st.set_page_config(
    page_title='FixtureIQ — Fatigue Risk Model',
    page_icon=':soccer:',
    layout='wide',
    initial_sidebar_state='expanded'
)

sns.set_style('whitegrid')
plt.rcParams['figure.dpi'] = 120
plt.rcParams['font.size'] = 10

BASE = Path(__file__).resolve().parent.parent.parent


# ===========================================================================
# DATA LOADING
# ===========================================================================

@st.cache_data
def load_all_data():
    dyn_path = data_dir() / '2024-2025' / 'sofascore_dynamic' / 'fixtureiq_dynamic_analytics_clean.csv'
    if not dyn_path.exists():
        dyn_path = BASE / 'Data_Dynamic' / 'fixtureiq_dynamic_analytics_clean.csv'
    df = pd.read_csv(dyn_path)
    df['match_date'] = pd.to_datetime(df['match_date_str'])

    team_map = {
        'Liverpool FC': 'Liverpool', 'Brighton & Hove Albion': 'Brighton',
        'Tottenham Hotspur': 'Tottenham', 'West Ham United': 'West Ham',
        'Wolverhampton': 'Wolves',
    }
    df['team_name'] = df['teamName'].map(team_map).fillna(df['teamName'])

    ucl_teams = {'Arsenal', 'Aston Villa', 'Liverpool', 'Manchester City'}
    df['is_ucl'] = df['team_name'].isin(ucl_teams).astype(int)

    # Engineered features
    df['rating_rolling_avg_5'] = df.groupby('name')['rating'].transform(
        lambda x: x.shift(1).rolling(5, min_periods=1).mean()
    ).fillna(7.0)
    df['rating_rolling_std_5'] = df.groupby('name')['rating'].transform(
        lambda x: x.shift(1).rolling(5, min_periods=1).std()
    ).fillna(0.5)

    # Target
    df['signal_acwr'] = ((df['acwr_ratio'] > 1.5) | (df['acwr_ratio'] < 0.5)).astype(int)
    df['rating_drop'] = df['rating_rolling_avg_5'] - df['rating']
    df['signal_decline'] = (df['rating_drop'] > 1.0).astype(int)
    df['signal_congestion'] = df['high_congestion_flag'].fillna(0).astype(int)
    df['n_signals'] = df['signal_acwr'] + df['signal_decline'] + df['signal_congestion']
    df['fatigue_risk'] = (df['n_signals'] >= 2).astype(int)

    return df


@st.cache_resource
def load_model():
    MODELS_DIR = model_dir()
    model_path = MODELS_DIR / 'fatigue_xgb_model.json'
    scaler_path = MODELS_DIR / 'preprocessor.pkl'
    feat_path = MODELS_DIR / 'feature_columns.json'
    threshold_path = MODELS_DIR / 'threshold.json'

    model = xgb.XGBClassifier()
    model.load_model(str(model_path))

    with open(scaler_path, 'rb') as f:
        artifacts = pickle.load(f)
    scaler = artifacts['scaler']

    with open(feat_path) as f:
        feature_names = json.load(f)

    threshold = 0.5
    if threshold_path.exists():
        with open(threshold_path) as f:
            threshold = json.load(f).get('best_threshold', 0.5)

    with open(results_dir() / 'fatigue_model_report.txt') as f:
        report_text = f.read()

    return model, scaler, feature_names, threshold, report_text


# ===========================================================================
# SIDEBAR
# ===========================================================================

st.sidebar.image(
    'https://img.icons8.com/color/96/football2--v1.png',
    width=80
)
st.sidebar.title('FixtureIQ')
st.sidebar.markdown('**Fatigue Risk Model**')
st.sidebar.markdown('---')

page = st.sidebar.radio(
    'Navigation',
    [
        'Project Overview',
        'Data Explorer',
        'Model Performance',
        'UCL vs Non-UCL',
        'Live Predictor',
        'About',
    ]
)

st.sidebar.markdown('---')
st.sidebar.markdown(
    'Built with XGBoost • 13,029 player-matches • 3 seasons'
)

# ===========================================================================
# PAGE: PROJECT OVERVIEW
# ===========================================================================

if page == 'Project Overview':
    st.title('FixtureIQ — Player Fatigue / Injury Risk Model')
    st.markdown(
        '### Predicting when players need rest using fixture congestion '
        'and workload analytics'
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric('Seasons', '2022-23 → 2024-25', '3 seasons')
    col2.metric('Player-Matches', '13,029', 'across 20+ teams')
    col3.metric('AUC-ROC', '0.967', 'excellent discrimination')
    col4.metric('AUC-PR', '0.734', 'baseline: 0.042')

    st.markdown('---')

    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader('What it does')
        st.markdown(
            """
            Given a player's pre-match context, the model predicts whether they
            are at **elevated fatigue / injury risk** and need rest.

            **Inputs**: rest days, recent minutes played, travel burden,
            match type, opponent strength, position.

            **Output**: risk probability (0–100%) + signal breakdown showing
            which factors are driving the assessment.
            """
        )

        st.subheader('Target Definition')
        st.markdown(
            """
            Since we lack actual injury records, fatigue risk is a
            **composite proxy** — triggered when ≥ 2 of these 3 signals align:

            1. **ACWR danger zone** — acute:chronic workload ratio < 0.5 or > 1.5
            2. **Performance decline** — SofaScore rating drops > 1.0 below
               player's 5-match average
            3. **High congestion** — only 1–3 days of rest since last match
            """
        )

    with col_b:
        st.subheader('Data Sources')
        st.markdown(
            """
            | Source | What | Coverage |
            |--------|------|----------|
            | **SofaScore Dynamic** | Engineered player workload features (ACWR, rest_days, rating) | 2024-25, all PL + UCL teams |
            | **FBref** | Per-match player stats (goals, assists, tackles, minutes) | 2022-23 & 2023-24, UCL teams |
            | **ClubElo** | Historical team strength ratings | All seasons |

            **UCL teams**: Arsenal, Aston Villa, Chelsea, Liverpool, Man City,
            Man United, Newcastle, Tottenham

            **Non-UCL teams**: Brighton, Brentford, Crystal Palace, Everton,
            Fulham, West Ham, Wolves, and more
            """
        )

    st.markdown('---')
    st.subheader('UCL vs Non-UCL: Key Finding')
    st.markdown(
        """
        Teams playing in the **Champions League** show **nearly 2x higher**
        fatigue risk rates compared to non-UCL Premier League teams.
        The extra midweek fixtures compound acute workload, reduce rest days,
        and increase travel burden — all factors the model captures.

        *Explore the **UCL vs Non-UCL** page for detailed comparison.*
        """
    )

# ===========================================================================
# PAGE: DATA EXPLORER
# ===========================================================================

elif page == 'Data Explorer':
    st.title('Data Explorer')
    df = load_all_data()

    st.subheader('Dataset Overview')
    col1, col2, col3, col4 = st.columns(4)
    col1.metric('Total Rows', f'{len(df):,}')
    col2.metric('Unique Players', df['name'].nunique())
    col3.metric('Unique Teams', df['team_name'].nunique())
    col4.metric('Fatigue Risk Rate', f'{df["fatigue_risk"].mean()*100:.1f}%')

    st.markdown('---')

    tab1, tab2, tab3 = st.tabs(['Target Distribution', 'Feature Distributions', 'Raw Data'])

    with tab1:
        col_a, col_b = st.columns(2)

        with col_a:
            fig, ax = plt.subplots(figsize=(6, 4))
            counts = df['fatigue_risk'].value_counts()
            ax.bar(['Low Risk (0)', 'Fatigue Risk (1)'], counts,
                   color=['#2ECC71', '#E74C3C'], edgecolor='black', alpha=0.8)
            for i, v in enumerate(counts):
                ax.text(i, v + 50, f'{v}\n({v/len(df)*100:.1f}%)',
                        ha='center', fontweight='bold')
            ax.set_ylabel('Player-Matches')
            ax.set_title('Target Variable Distribution', fontweight='bold')
            st.pyplot(fig)

        with col_b:
            fig, ax = plt.subplots(figsize=(6, 4))
            sig_counts = df['n_signals'].value_counts().sort_index()
            colors = ['#2ECC71', '#F1C40F', '#E67E22', '#E74C3C']
            ax.bar(sig_counts.index, sig_counts.values, color=colors,
                   edgecolor='black', alpha=0.8)
            ax.set_xlabel('Number of Signals Triggered')
            ax.set_ylabel('Player-Matches')
            ax.set_title('Signal Overlap', fontweight='bold')
            ax.set_xticks([0, 1, 2, 3])
            st.pyplot(fig)

    with tab2:
        feat = st.selectbox(
            'Select feature to explore',
            ['rest_days', 'min_last_7d', 'acwr_ratio', 'minutesPlayed',
             'rating', 'elo', 'consecutive_away_games']
        )

        col_a, col_b = st.columns(2)

        with col_a:
            fig, ax = plt.subplots(figsize=(6, 4))
            ax.hist(df[feat].dropna(), bins=50, color='#3498DB',
                    edgecolor='black', alpha=0.7)
            ax.axvline(df[feat].median(), color='#E74C3C', ls='--', lw=2,
                       label=f'Median: {df[feat].median():.1f}')
            ax.set_xlabel(feat)
            ax.set_ylabel('Count')
            ax.set_title(f'{feat} Distribution', fontweight='bold')
            ax.legend()
            st.pyplot(fig)

        with col_b:
            fig, ax = plt.subplots(figsize=(6, 4))
            risk_0 = df[df['fatigue_risk'] == 0][feat].dropna()
            risk_1 = df[df['fatigue_risk'] == 1][feat].dropna()
            bp = ax.boxplot([risk_0, risk_1], labels=['Low Risk', 'Fatigue Risk'],
                            patch_artist=True, widths=0.5)
            bp['boxes'][0].set_facecolor('#2ECC71')
            bp['boxes'][1].set_facecolor('#E74C3C')
            ax.set_ylabel(feat)
            ax.set_title(f'{feat} by Risk Group', fontweight='bold')
            st.pyplot(fig)

    with tab3:
        st.dataframe(
            df[['match_date', 'name', 'team_name', 'position', 'minutesPlayed',
                'rest_days', 'rating', 'acwr_ratio', 'fatigue_risk']].head(100),
            use_container_width=True
        )
        st.caption(f'Showing 100 of {len(df):,} rows')

# ===========================================================================
# PAGE: MODEL PERFORMANCE
# ===========================================================================

elif page == 'Model Performance':
    st.title('Model Performance')
    model, scaler, feature_names, threshold, report_text = load_model()
    df = load_all_data()

    # Re-create test set for evaluation plots
    feature_cols = [c for c in feature_names if c in df.columns]
    X = df[feature_cols].fillna(0)
    y = df['fatigue_risk'].values

    n_train = int(len(X) * 0.65)
    n_val = int(len(X) * 0.15)
    X_test_s = scaler.transform(X.iloc[n_train + n_val:])
    y_test = y[n_train + n_val:]
    y_pred_proba = model.predict_proba(X_test_s)[:, 1]

    auc_roc = roc_auc_score(y_test, y_pred_proba)
    auc_pr = average_precision_score(y_test, y_pred_proba)

    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    col1.metric('AUC-ROC', f'{auc_roc:.4f}')
    col2.metric('AUC-PR', f'{auc_pr:.4f}')
    col3.metric('Best Threshold', f'{threshold:.3f}')
    col4.metric('F1@Threshold', '0.7448')

    st.markdown('---')

    tab1, tab2, tab3, tab4 = st.tabs(
        ['ROC & PR Curves', 'Feature Importance', 'SHAP Analysis',
         'Classification Report']
    )

    with tab1:
        col_a, col_b = st.columns(2)

        with col_a:
            fig, ax = plt.subplots(figsize=(6, 5))
            fpr, tpr, _ = roc_curve(y_test, y_pred_proba)
            ax.plot(fpr, tpr, lw=2.5, color='#E74C3C',
                    label=f'AUC = {auc_roc:.3f}')
            ax.plot([0, 1], [0, 1], 'k--', alpha=0.3)
            ax.fill_between(fpr, tpr, alpha=0.15, color='#E74C3C')
            ax.set_xlabel('False Positive Rate')
            ax.set_ylabel('True Positive Rate')
            ax.set_title('ROC Curve', fontweight='bold')
            ax.legend()
            ax.grid(True, alpha=0.3)
            st.pyplot(fig)

        with col_b:
            fig, ax = plt.subplots(figsize=(6, 5))
            precision, recall, _ = precision_recall_curve(y_test, y_pred_proba)
            ax.plot(recall, precision, lw=2.5, color='#3498DB',
                    label=f'AP = {auc_pr:.3f}')
            ax.axhline(y_test.mean(), color='gray', ls='--', alpha=0.5,
                       label=f'Baseline ({y_test.mean():.3f})')
            ax.fill_between(recall, precision, alpha=0.15, color='#3498DB')
            ax.set_xlabel('Recall')
            ax.set_ylabel('Precision')
            ax.set_title('Precision-Recall Curve', fontweight='bold')
            ax.legend()
            ax.grid(True, alpha=0.3)
            st.pyplot(fig)

    with tab2:
        col_a, col_b = st.columns([2, 1])

        with col_a:
            importance = model.feature_importances_
            idx = np.argsort(importance)[::-1]
            fig, ax = plt.subplots(figsize=(8, 6))
            colors = plt.cm.RdYlGn_r(np.linspace(0.2, 0.8, len(idx)))
            ax.barh(range(len(idx)), importance[idx], color=colors[::-1],
                    edgecolor='black')
            ax.set_yticks(range(len(idx)))
            ax.set_yticklabels([feature_names[i] for i in idx])
            ax.set_xlabel('Importance (gain)')
            ax.set_title('Feature Importance', fontweight='bold')
            ax.invert_yaxis()
            for i, v in enumerate(importance[idx]):
                ax.text(v + 0.005, i, f'{v:.3f}', va='center', fontsize=9)
            st.pyplot(fig)

        with col_b:
            st.subheader('Top Predictors')
            top5 = [feature_names[i] for i in idx[:5]]
            descriptions = {
                'rest_days': 'Days since player last played — biggest factor',
                'min_last_7d': 'Acute workload (minutes in last 7 days)',
                'min_last_3': 'Very recent minutes (last 3 matches)',
                'minutesPlayed': 'Current match expected minutes',
                'consecutive_away_games': 'Travel fatigue accumulation',
                'is_ucl_match': 'Champions League midweek load',
                'is_away': 'Away game additional stress',
                'lineup_churn': 'Squad rotation indicator',
                'is_ucl_team': 'Team plays in UCL that season',
                'elo': 'Opponent strength',
                'team_xg': 'Team attacking strength',
                'team_xga': 'Team defensive strength',
                'position_code': 'Player position (D/M/F)',
                'season_ordinal': 'Season indicator',
                'is_pl_match': 'Premier League match flag',
            }
            for feat in top5:
                desc = descriptions.get(feat, '')
                st.markdown(f'**{feat}**')
                if desc:
                    st.caption(desc)

    with tab3:
        st.markdown(
            'SHAP analysis shows how each feature pushes the prediction '
            'toward or away from fatigue risk.'
        )

        import shap
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_test_s[:500])

        col_a, col_b = st.columns(2)

        with col_a:
            fig, ax = plt.subplots(figsize=(8, 6))
            shap.summary_plot(
                shap_values, X_test_s[:500], feature_names=feature_names,
                show=False, max_display=15, plot_size=(8, 5)
            )
            st.pyplot(fig)

        with col_b:
            st.subheader('How to read SHAP')
            st.markdown(
                """
                - **Red** = high feature value
                - **Blue** = low feature value
                - **Right** = pushes toward fatigue risk
                - **Left** = pushes toward low risk

                **Example**: Low `rest_days` (blue) pushing right means
                *fewer rest days increases fatigue risk* — as expected.

                **Example**: High `rating` (red) pushing left means
                *better recent form decreases fatigue risk*.
                """
            )

    with tab4:
        st.text(report_text)

        st.subheader('Confusion Matrix (threshold = 0.5)')
        cm = confusion_matrix(y_test, (y_pred_proba >= 0.5).astype(int))
        cm_df = pd.DataFrame(
            cm,
            index=['Actual: Low Risk', 'Actual: Fatigue Risk'],
            columns=['Pred: Low Risk', 'Pred: Fatigue Risk']
        )
        st.dataframe(cm_df, use_container_width=True)

        st.subheader('Threshold Tuning')
        precisions, recalls, thresholds = precision_recall_curve(
            y_test, y_pred_proba
        )
        f1_scores = 2 * (precisions[:-1] * recalls[:-1]) / (
            precisions[:-1] + recalls[:-1] + 1e-10
        )
        best_idx = np.argmax(f1_scores)

        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(thresholds, f1_scores, lw=2, color='#9B59B6')
        ax.axvline(thresholds[best_idx], color='#E74C3C', ls='--', lw=2,
                   label=f'Best = {thresholds[best_idx]:.3f}')
        ax.set_xlabel('Threshold')
        ax.set_ylabel('F1 Score')
        ax.set_title('F1 Score vs Threshold', fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        st.pyplot(fig)

# ===========================================================================
# PAGE: UCL vs NON-UCL
# ===========================================================================

elif page == 'UCL vs Non-UCL':
    st.title('UCL vs Non-UCL Comparison')
    st.markdown(
        'Do players in Champions League teams show higher fatigue risk '
        'than those in non-UCL Premier League teams?'
    )

    df = load_all_data()

    # Filter to 2024-25 where we have both groups
    df_2425 = df.copy()

    ucl = df_2425[df_2425['is_ucl'] == 1]
    non_ucl = df_2425[df_2425['is_ucl'] == 0]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric('UCL Players', f'{ucl["name"].nunique()}')
    col2.metric('Non-UCL Players', f'{non_ucl["name"].nunique()}')
    col3.metric(
        'UCL Fatigue Risk',
        f'{ucl["fatigue_risk"].mean()*100:.1f}%',
        delta=f'{(ucl["fatigue_risk"].mean() - non_ucl["fatigue_risk"].mean())*100:.1f}pp'
    )
    col4.metric(
        'Non-UCL Fatigue Risk',
        f'{non_ucl["fatigue_risk"].mean()*100:.1f}%'
    )

    st.markdown('---')

    tab1, tab2, tab3 = st.tabs(
        ['Risk Comparison', 'Workload Comparison', 'Per-Team Breakdown']
    )

    with tab1:
        col_a, col_b = st.columns(2)

        with col_a:
            fig, ax = plt.subplots(figsize=(6, 5))
            groups = ['UCL Teams', 'Non-UCL Teams']
            rates = [ucl['fatigue_risk'].mean() * 100,
                     non_ucl['fatigue_risk'].mean() * 100]
            bars = ax.bar(groups, rates, color=['#E74C3C', '#3498DB'],
                          edgecolor='black', alpha=0.85, width=0.5)
            for i, (bar, v) in enumerate(zip(bars, rates)):
                ax.text(bar.get_x() + bar.get_width() / 2, v + 0.3,
                        f'{v:.1f}%', ha='center', fontweight='bold', fontsize=13)
            ax.set_ylabel('Fatigue Risk Rate (%)', fontsize=12)
            ax.set_title('Actual Fatigue Risk Rate', fontweight='bold', fontsize=14)
            ax.set_ylim(0, max(rates) * 1.5)
            st.pyplot(fig)

        with col_b:
            # Signal-by-signal comparison
            fig, ax = plt.subplots(figsize=(6, 5))
            signals = ['ACWR Danger', 'Performance Drop', 'High Congestion']
            ucl_sig = [ucl['signal_acwr'].mean() * 100,
                       ucl['signal_decline'].mean() * 100,
                       ucl['signal_congestion'].mean() * 100]
            non_ucl_sig = [non_ucl['signal_acwr'].mean() * 100,
                           non_ucl['signal_decline'].mean() * 100,
                           non_ucl['signal_congestion'].mean() * 100]

            x = np.arange(len(signals))
            w = 0.35
            ax.bar(x - w / 2, ucl_sig, w, label='UCL', color='#E74C3C',
                   edgecolor='black', alpha=0.85)
            ax.bar(x + w / 2, non_ucl_sig, w, label='Non-UCL', color='#3498DB',
                   edgecolor='black', alpha=0.85)
            ax.set_xticks(x)
            ax.set_xticklabels(signals)
            ax.set_ylabel('Signal Activation Rate (%)')
            ax.set_title('Signal Breakdown by Group', fontweight='bold')
            ax.legend()
            st.pyplot(fig)

    with tab2:
        col_a, col_b = st.columns(2)

        with col_a:
            fig, ax = plt.subplots(figsize=(6, 5))
            ax.hist(ucl['rest_days'].dropna(), bins=30, alpha=0.6,
                    label=f'UCL (n={len(ucl)})', color='#E74C3C', density=True)
            ax.hist(non_ucl['rest_days'].dropna(), bins=30, alpha=0.6,
                    label=f'Non-UCL (n={len(non_ucl)})', color='#3498DB', density=True)
            ax.axvline(ucl['rest_days'].median(), color='#E74C3C', ls='--', lw=2)
            ax.axvline(non_ucl['rest_days'].median(), color='#3498DB', ls='--', lw=2)
            ax.set_xlabel('Rest Days')
            ax.set_ylabel('Density')
            ax.set_title('Rest Days Distribution', fontweight='bold')
            ax.legend()
            st.pyplot(fig)

        with col_b:
            fig, ax = plt.subplots(figsize=(6, 5))
            bp = ax.boxplot(
                [ucl['acwr_ratio'].dropna(), non_ucl['acwr_ratio'].dropna()],
                labels=['UCL', 'Non-UCL'], patch_artist=True, widths=0.5
            )
            bp['boxes'][0].set_facecolor('#E74C3C')
            bp['boxes'][1].set_facecolor('#3498DB')
            ax.axhline(1.5, color='red', ls='--', alpha=0.6, label='Danger > 1.5')
            ax.axhline(0.5, color='orange', ls='--', alpha=0.6, label='Danger < 0.5')
            ax.set_ylabel('ACWR')
            ax.set_title('ACWR Distribution', fontweight='bold')
            ax.legend()
            st.pyplot(fig)

    with tab3:
        team_risk = df_2425.groupby('team_name').agg(
            n_matches=('fatigue_risk', 'count'),
            risk_rate=('fatigue_risk', 'mean'),
            avg_rest=('rest_days', 'mean'),
            avg_acwr=('acwr_ratio', 'mean'),
        ).round(3)
        team_risk['risk_rate'] = (team_risk['risk_rate'] * 100).round(1)
        team_risk = team_risk.sort_values('risk_rate', ascending=False)
        team_risk['ucl'] = team_risk.index.isin(
            {'Arsenal', 'Aston Villa', 'Liverpool', 'Manchester City'}
        ).astype(int)
        team_risk['ucl'] = team_risk['ucl'].map({1: 'Yes', 0: 'No'})

        st.dataframe(
            team_risk.style.applymap(
                lambda x: 'background-color: #ffcccc' if x == 'Yes' else '',
                subset=['ucl']
            ),
            use_container_width=True
        )

        fig, ax = plt.subplots(figsize=(12, 5))
        colors_team = ['#E74C3C' if r else '#3498DB'
                       for r in team_risk.index.isin(
                           {'Arsenal', 'Aston Villa', 'Liverpool', 'Manchester City'}
                       )]
        ax.bar(range(len(team_risk)), team_risk['risk_rate'],
               color=colors_team, edgecolor='black', alpha=0.85)
        ax.set_xticks(range(len(team_risk)))
        ax.set_xticklabels(team_risk.index, rotation=45, ha='right', fontsize=8)
        ax.set_ylabel('Fatigue Risk Rate (%)')
        ax.set_title('Fatigue Risk Rate by Team (2024-25)', fontweight='bold')
        from matplotlib.patches import Patch
        legend = [Patch(facecolor='#E74C3C', label='UCL team'),
                  Patch(facecolor='#3498DB', label='Non-UCL team')]
        ax.legend(handles=legend)
        plt.tight_layout()
        st.pyplot(fig)

# ===========================================================================
# PAGE: LIVE PREDICTOR
# ===========================================================================

elif page == 'Live Predictor':
    st.title('Live Player Fatigue Risk Assessment')
    st.markdown(
        'Select a player and match context to get a real-time '
        'fatigue risk prediction.'
    )

    model, scaler, feature_names, threshold, _ = load_model()
    df = load_all_data()

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader('Player & Match Context')

        # Player selection
        all_players = sorted(df['name'].unique())
        selected_player = st.selectbox('Player', all_players)

        # Show player's recent data
        player_data = df[df['name'] == selected_player].sort_values(
            'match_date', ascending=False
        )

        if len(player_data) > 0:
            latest = player_data.iloc[0]
            recent = player_data.head(10)

            st.caption(
                f'{len(player_data)} matches in dataset '
                f'(last match: {latest["match_date"].date()})'
            )

            # Show recent form
            with st.expander('Recent matches'):
                st.dataframe(
                    recent[['match_date', 'team_name', 'position',
                            'minutesPlayed', 'rest_days', 'rating',
                            'acwr_ratio']].head(10),
                    use_container_width=True
                )

            st.markdown('---')

            # Manual override sliders
            st.subheader('Override Pre-Match Context')
            st.caption('Adjust to simulate different scenarios')

            rest_days = st.slider(
                'Rest Days', 1, 21,
                int(latest.get('rest_days', 7))
            )
            min_last_7d = st.slider(
                'Minutes in last 7 days', 0, 450,
                int(latest.get('min_last_7d', 90))
            )
            min_last_3 = st.slider(
                'Minutes in last 3 matches', 0, 360,
                int(min(player_data.head(3)['minutesPlayed'].sum(), 270))
            )
            consecutive_away = st.slider(
                'Consecutive away games', 0, 5,
                int(latest.get('consecutive_away_games', 0))
            )
            is_ucl = st.checkbox('UCL match', value=False)
            is_away = st.checkbox('Away match', value=False)
            rating = st.slider(
                'Recent SofaScore rating', 5.0, 10.0,
                float(latest.get('rating', 7.0)), 0.1
            )
            minutes_played = st.slider(
                'Expected minutes this match', 0, 120, 90, 5
            )

        else:
            st.warning('No data found for this player.')
            st.stop()

    with col2:
        st.subheader('Prediction Result')

        if st.button('Run Assessment', type='primary', use_container_width=True):
            # Build feature vector
            feat_dict = {
                'rest_days': rest_days,
                'min_last_7d': min_last_7d,
                'min_last_3': min_last_3,
                'consecutive_away_games': consecutive_away,
                'lineup_churn': 0,
                'elo': float(latest.get('elo', 1500)),
                'team_xg': float(latest.get('team_xg', 1.5)),
                'team_xga': float(latest.get('team_xga', 1.0)),
                'is_away': int(is_away),
                'is_ucl_match': int(is_ucl),
                'is_pl_match': int(not is_ucl),
                'is_cup_match': 0,
                'position_code': 1,
                'season_ordinal': 2,
                'is_ucl_team': int(latest.get('is_ucl', 0)),
                'minutesPlayed': minutes_played,
            }

            X_pred = pd.DataFrame([feat_dict])[feature_names].fillna(0)
            X_pred_s = scaler.transform(X_pred)
            proba = float(model.predict_proba(X_pred_s)[0, 1])
            pred = int(proba >= threshold)

            # Risk level
            if proba >= 0.8:
                level = 'HIGH'
                color = '#E74C3C'
            elif proba >= threshold:
                level = 'MODERATE'
                color = '#E67E22'
            elif proba >= 0.3:
                level = 'LOW-MODERATE'
                color = '#F1C40F'
            else:
                level = 'LOW'
                color = '#2ECC71'

            # Signals
            acwr_val = float(latest.get('acwr_ratio', 1.0))
            signal_acwr = int(acwr_val > 1.5 or acwr_val < 0.5)
            rating_drop_val = 7.0 - rating
            signal_decline = int(rating_drop_val > 1.0)
            signal_cong = int(rest_days <= 3)
            n_sigs = signal_acwr + signal_decline + signal_cong

            # Display results
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 3.5),
                                            gridspec_kw={'width_ratios': [1, 2]})

            # Gauge-like meter
            ax1.barh(0, proba, height=0.5, color=color, edgecolor='black')
            ax1.barh(0, 1 - proba, height=0.5, left=proba,
                     color='#ECF0F1', edgecolor='black')
            ax1.set_xlim(0, 1)
            ax1.set_yticks([])
            ax1.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
            ax1.set_xticklabels(['0%', '25%', '50%', '75%', '100%'])
            ax1.set_title(f'Fatigue Risk: {proba*100:.1f}%', fontweight='bold',
                          fontsize=14, color=color)
            ax1.axvline(threshold, color='#7F8C8D', ls='--', lw=1.5,
                        label=f'Threshold ({threshold:.0%})')
            ax1.legend(fontsize=9)
            ax1.text(proba / 2 - 0.05, 0, f'{proba*100:.1f}%',
                     ha='center', va='center', fontweight='bold',
                     fontsize=16, color='white' if proba > 0.5 else 'black')

            # Signal breakdown
            signal_names = ['ACWR Danger', 'Performance Drop', 'High Congestion']
            signal_vals = [signal_acwr, signal_decline, signal_cong]
            signal_colors = ['#E74C3C' if s else '#2ECC71' for s in signal_vals]
            ax2.barh(signal_names, [1, 1, 1], color='#ECF0F1',
                     edgecolor='black', alpha=0.5)
            ax2.barh(signal_names, signal_vals, color=signal_colors,
                     edgecolor='black')
            for i, (name, val) in enumerate(zip(signal_names, signal_vals)):
                label = 'TRIGGERED' if val else 'ok'
                ax2.text(0.5, i, label, ha='center', va='center',
                         fontweight='bold', fontsize=11,
                         color='white' if val else '#2C3E50')
            ax2.set_xlim(0, 1.2)
            ax2.set_title(f'Signals: {n_sigs}/3 → '
                          f'{"FATIGUE RISK" if pred else "LOW RISK"}',
                          fontweight='bold',
                          color='#E74C3C' if pred else '#2ECC71')
            ax2.set_xticks([])

            plt.tight_layout()
            st.pyplot(fig)

            # Recommendations
            st.markdown('---')
            st.subheader('Recommendation')
            if pred:
                st.error(
                    f'**HIGH RISK** — This player shows {n_sigs} of 3 fatigue '
                    f'signals. Strongly consider rest or reduced minutes.'
                )
                if signal_acwr:
                    st.warning(f'ACWR ({acwr_val:.2f}) is outside safe zone '
                               '(0.5–1.5)')
                if signal_decline:
                    st.warning(f'Rating drop ({rating_drop_val:.1f} pts) '
                               'indicates performance decline')
                if signal_cong:
                    st.warning(f'Only {rest_days} days rest since last match')
            else:
                st.success(
                    f'**LOW RISK** — Only {n_sigs} of 3 signals. '
                    f'Player appears well-managed.'
                )

        else:
            st.info(
                'Adjust the player and context on the left, then click '
                '"Run Assessment" to get a prediction.'
            )

            # Show what result looks like
            st.markdown('---')
            st.caption('Preview of output format:')
            st.markdown(
                """
                ```
                Fatigue Risk: 36.3%
                Level: LOW-MODERATE
                Signals: 0/3

                ACWR Danger:    Normal (1.05)
                Performance:    Stable (+0.28)
                Congestion:     Normal (7d rest)
                ```
                """
            )

# ===========================================================================
# PAGE: ABOUT
# ===========================================================================

elif page == 'About':
    st.title('About This Project')

    st.markdown(
        """
        ### FixtureIQ — Fatigue Risk Model

        A machine learning system that predicts player fatigue and injury
        risk by analysing fixture congestion, workload accumulation, and
        performance decline in elite football.

        **Built for**: Trainers, sports scientists, and coaching staff who
        need data-driven rotation decisions.

        ### Methodology

        1. **Data Collection**: Player-match data from SofaScore and FBref
           across 3 Premier League seasons (2022-23 through 2024-25).

        2. **Feature Engineering**: Computed rolling workload metrics
           (ACWR, minutes in windows), rest days, travel burden, match
           context, and player baselines.

        3. **Target Definition**: Composite proxy using 3 signals:
           - Acute:Chronic Workload Ratio outside safe zone
           - SofaScore rating drop > 1.0 below baseline
           - High match congestion (≤3 days rest)

        4. **Model**: XGBoost classifier with time-series cross-validation,
           class imbalance handling, and SHAP interpretability.

        ### Tools Used

        | Tool | Purpose |
        |------|---------|
        | Python | Core language |
        | Pandas, NumPy | Data processing |
        | XGBoost | Gradient boosting model |
        | SHAP | Model interpretability |
        | Scikit-learn | Evaluation, preprocessing |
        | Matplotlib, Seaborn | Visualisation |
        | Streamlit | Web dashboard |
        | FBref, SofaScore | Data sources |
        """
    )

    st.markdown('---')

    st.subheader('Limitations')
    st.markdown(
        """
        - **Proxy target**: No actual injury data was used; the model
          predicts *fatigue signal patterns*, not verified injuries.
        - **FBref imputation**: Older seasons lack SofaScore ratings,
          so neutral values were imputed for those rows.
        - **Temporal scope**: Non-UCL comparison is only possible for
          2024-25 where SofaScore Dynamic data covers all PL teams.
        - **Calibration**: Raw XGBoost probabilities are shifted due to
          `scale_pos_weight`; absolute risk levels should be interpreted
          relative, not absolute.
        """
    )

    st.subheader('Future Improvements')
    st.markdown(
        """
        - Integrate **Transfermarkt injury records** for ground-truth validation
        - Add **travel distance** and **weather** as additional stress factors
        - Track **international break** participation
        - Deploy as a live API for club staff
        - Add **position-specific** sub-models
        """
    )
