"""
FixtureIQ - Model Evaluation
==============================
Evaluation metrics, plots, SHAP analysis, and UCL comparison.
"""

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.metrics import (
    classification_report, confusion_matrix, roc_auc_score,
    average_precision_score, precision_recall_curve, roc_curve,
)

_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from src.config.paths import results_dir

warnings.filterwarnings('ignore')
sns.set_style('whitegrid')
plt.rcParams['figure.figsize'] = (12, 6)


def evaluate_model(model, scaler, X_sets, y_sets, feature_names, df_test, target_name="fatigue"):
    label = "Injury Risk" if target_name == "injury" else "Fatigue Risk"
    print('\n' + '=' * 70)
    print(f'MODEL EVALUATION ({label})')
    print('=' * 70)

    X_train_scaled, X_val_scaled, X_test_scaled = X_sets
    y_train, y_val, y_test = y_sets

    y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
    y_pred = (y_pred_proba >= 0.5).astype(int)

    auc_roc = roc_auc_score(y_test, y_pred_proba)
    auc_pr = average_precision_score(y_test, y_pred_proba)

    print(f'\n  AUC-ROC: {auc_roc:.4f}')
    print(f'  AUC-PR:  {auc_pr:.4f}')
    print(f'\n  Classification Report (threshold=0.5):')
    print(classification_report(y_test, y_pred, target_names=['Low Risk', label]))

    RESULTS_DIR = results_dir()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    report_path = RESULTS_DIR / f'{target_name}_model_report.txt'
    with open(report_path, 'w') as f:
        f.write(f'FIXTURE IQ - {label.upper()} MODEL REPORT\n')
        f.write('=' * 50 + '\n\n')
        f.write(f'AUC-ROC: {auc_roc:.4f}\n')
        f.write(f'AUC-PR:  {auc_pr:.4f}\n\n')
        f.write('Classification Report:\n')
        f.write(classification_report(y_test, y_pred, target_names=['Low Risk', label]))
        f.write('\n\nConfusion Matrix:\n')
        cm = confusion_matrix(y_test, y_pred)
        f.write(f'TN={cm[0,0]}  FP={cm[0,1]}\n')
        f.write(f'FN={cm[1,0]}  TP={cm[1,1]}\n')
    print(f'  Report saved: {report_path}')

    _plot_feature_importance(model, feature_names)
    _plot_shap(model, X_test_scaled, feature_names)
    _plot_roc_pr(y_test, y_pred_proba)

    if 'is_ucl_team' in df_test.columns:
        target_col = "injury_flag" if target_name == "injury" else "fatigue_risk"
        _plot_ucl_comparison(model, scaler, df_test, feature_names, target_col)

    return y_test, y_pred_proba


def _plot_feature_importance(model, feature_names):
    RESULTS_DIR = results_dir()
    importance = model.feature_importances_
    idx = np.argsort(importance)[::-1]

    fig, ax = plt.subplots(figsize=(10, 8))
    colors = plt.cm.RdYlGn_r(np.linspace(0.2, 0.8, len(idx)))
    ax.barh(range(len(idx)), importance[idx], color=colors[::-1])
    ax.set_yticks(range(len(idx)))
    ax.set_yticklabels([feature_names[i] for i in idx])
    ax.set_xlabel('Feature Importance (gain)')
    ax.set_title('XGBoost Feature Importance - Fatigue Risk Model')
    ax.invert_yaxis()
    plt.tight_layout()
    fig.savefig(RESULTS_DIR / 'figures' / 'feature_importance.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f'  Feature importance plot: {RESULTS_DIR / "figures" / "feature_importance.png"}')


def _plot_shap(model, X_test_scaled, feature_names):
    RESULTS_DIR = results_dir()
    try:
        import shap
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_test_scaled)
        fig, ax = plt.subplots(figsize=(10, 8))
        shap.summary_plot(
            shap_values, X_test_scaled, feature_names=feature_names,
            show=False, max_display=15, plot_size=(10, 6)
        )
        plt.tight_layout()
        fig.savefig(RESULTS_DIR / 'figures' / 'shap_summary.png', dpi=150, bbox_inches='tight')
        plt.close()
        print(f'  SHAP summary plot: {RESULTS_DIR / "figures" / "shap_summary.png"}')
    except Exception as e:
        print(f'  [WARN] SHAP plot failed: {e}')


def _plot_roc_pr(y_test, y_pred_proba):
    RESULTS_DIR = results_dir()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    fpr, tpr, _ = roc_curve(y_test, y_pred_proba)
    auc_val = roc_auc_score(y_test, y_pred_proba)
    ax1.plot(fpr, tpr, lw=2, label=f'AUC = {auc_val:.3f}')
    ax1.plot([0, 1], [0, 1], 'k--', alpha=0.3)
    ax1.set_xlabel('False Positive Rate')
    ax1.set_ylabel('True Positive Rate')
    ax1.set_title('ROC Curve')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    precision, recall, _ = precision_recall_curve(y_test, y_pred_proba)
    ap_val = average_precision_score(y_test, y_pred_proba)
    ax2.plot(recall, precision, lw=2, label=f'AP = {ap_val:.3f}')
    ax2.axhline(y_test.mean(), color='k', linestyle='--', alpha=0.3, label=f'Baseline ({y_test.mean():.2f})')
    ax2.set_xlabel('Recall')
    ax2.set_ylabel('Precision')
    ax2.set_title('Precision-Recall Curve')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(RESULTS_DIR / 'figures' / 'roc_pr_curves.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f'  ROC/PR curves: {RESULTS_DIR / "figures" / "roc_pr_curves.png"}')


def _plot_ucl_comparison(model, scaler, df_test, feature_names, target_col="fatigue_risk"):
    RESULTS_DIR = results_dir()
    print('\n' + '=' * 70)
    print('UCL vs NON-UCL COMPARISON')
    print('=' * 70)

    if 'is_ucl_team' not in df_test.columns:
        return

    ucl_mask = df_test['is_ucl_team'] == 1
    non_ucl_mask = ~ucl_mask if 'is_non_ucl_team' not in df_test.columns else df_test['is_non_ucl_team'] == 1

    if ucl_mask.sum() == 0 or non_ucl_mask.sum() == 0:
        print('  [INFO] Insufficient UCL/non-UCL data in test set for comparison.')
        return

    if target_col not in df_test.columns:
        target_col = "injury_flag" if "injury_flag" in df_test.columns else "fatigue_risk"

    feature_cols = [c for c in feature_names if c in df_test.columns]
    X_test_u = scaler.transform(df_test.loc[ucl_mask, feature_cols].fillna(0))
    X_test_nu = scaler.transform(df_test.loc[non_ucl_mask, feature_cols].fillna(0))
    y_test_u = df_test.loc[ucl_mask, target_col].values
    y_test_nu = df_test.loc[non_ucl_mask, target_col].values

    proba_u = model.predict_proba(X_test_u)[:, 1]
    proba_nu = model.predict_proba(X_test_nu)[:, 1]

    print(f'  UCL teams:     {len(proba_u)} samples, actual risk rate={y_test_u.mean():.1%}')
    print(f'  Non-UCL teams: {len(proba_nu)} samples, actual risk rate={y_test_nu.mean():.1%}')
    print(f'  UCL predicted risk:     {proba_u.mean():.1%}')
    print(f'  Non-UCL predicted risk: {proba_nu.mean():.1%}')

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    axes[0].hist(proba_u, bins=30, alpha=0.6, label='UCL teams', color='#E74C3C', density=True)
    axes[0].hist(proba_nu, bins=30, alpha=0.6, label='Non-UCL teams', color='#3498DB', density=True)
    axes[0].axvline(proba_u.mean(), color='#E74C3C', ls='--', lw=2)
    axes[0].axvline(proba_nu.mean(), color='#3498DB', ls='--', lw=2)
    axes[0].set_xlabel('Predicted Fatigue Risk Probability')
    axes[0].set_ylabel('Density')
    axes[0].set_title('Risk Score Distribution')
    axes[0].legend()

    groups = ['UCL Teams', 'Non-UCL Teams']
    actual_rates = [y_test_u.mean() * 100, y_test_nu.mean() * 100]
    pred_rates = [proba_u.mean() * 100, proba_nu.mean() * 100]
    x = range(len(groups))
    axes[1].bar(x, actual_rates, width=0.35, label='Actual', color='#2C3E50', alpha=0.8)
    axes[1].bar([i + 0.35 for i in x], pred_rates, width=0.35, label='Predicted', color='#E67E22', alpha=0.8)
    axes[1].set_xticks([i + 0.175 for i in x])
    axes[1].set_xticklabels(groups)
    axes[1].set_ylabel('Fatigue Risk Rate (%)')
    axes[1].set_title('Actual vs Predicted Risk Rate')
    axes[1].legend()

    if 'acwr_ratio' in df_test.columns:
        ucl_acwr = df_test.loc[ucl_mask, 'acwr_ratio'].dropna()
        non_ucl_acwr = df_test.loc[non_ucl_mask, 'acwr_ratio'].dropna()
        axes[2].boxplot([ucl_acwr, non_ucl_acwr], labels=['UCL', 'Non-UCL'])
        axes[2].axhline(1.5, color='r', ls='--', alpha=0.5, label='Danger threshold')
        axes[2].axhline(0.5, color='r', ls='--', alpha=0.5)
        axes[2].set_ylabel('ACWR')
        axes[2].set_title('ACWR Distribution by Group')
        axes[2].legend()

    plt.tight_layout()
    fig.savefig(RESULTS_DIR / 'figures' / 'ucl_vs_non_ucl_comparison.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f'  UCL comparison plot: {RESULTS_DIR / "figures" / "ucl_vs_non_ucl_comparison.png"}')
