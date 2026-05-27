"""
CLI entry point for FixtureIQ Dynamic Congestion Pipeline.
"""
import sys
from pathlib import Path
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import argparse
from src.data.dynamic_pipeline import FixtureIQDynamicPipeline


def main():
    parser = argparse.ArgumentParser(description="FixtureIQ Fully Dynamic Season Baseline Mapper")
    parser.add_argument("--year", default="24/25", help="SofaScore short season code (e.g. 24/25)")
    parser.add_argument("--output-dir", default=None, help="Export folder (defaults to data/<season>/sofascore_dynamic/)")
    parser.add_argument("--delay", type=float, default=3.0, help="Delay between API calls")
    args = parser.parse_args()

    pipeline = FixtureIQDynamicPipeline(year_sofascore=args.year, output_dir=args.output_dir, delay=args.delay)
    master_df = pipeline.execute_pipeline()
    pipeline.export(master_df)


if __name__ == '__main__':
    main()
