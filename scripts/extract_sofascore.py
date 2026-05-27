"""
CLI entry point for SofaScore player performance pipeline.
"""
import sys
from pathlib import Path
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from src.data.sofascore_pipeline import main

if __name__ == '__main__':
    main()
