"""
CLI entry point for training the XGBoost fatigue risk model.

Usage:
    python scripts/train_model.py
"""
import sys
from pathlib import Path
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Train XGBoost fatigue risk model')
    parser.add_argument('--help-model', action='store_true', help=argparse.SUPPRESS)
    args, _ = parser.parse_known_args()

    from src.models.train import main
    main()
