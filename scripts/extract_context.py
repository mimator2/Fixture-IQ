"""
CLI entry point for ClubElo/Understat contextual data extraction.
"""
import sys
from pathlib import Path
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from src.data.context_extractor import main

if __name__ == '__main__':
    main()
