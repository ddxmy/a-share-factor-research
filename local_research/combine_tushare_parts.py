#!/usr/bin/env python3
"""Combine audited Tushare parquet batches into the single backtest input."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parts-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    parts = sorted(Path(args.parts_dir).glob("*.parquet"))
    if not parts:
        raise ValueError("No parquet batches found")
    panel = pd.concat((pd.read_parquet(p) for p in parts), ignore_index=True)
    panel = panel.drop_duplicates(["dt", "Ticker"]).sort_values(["dt", "Ticker"])
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(output, index=False)
    print(f"Combined {len(parts)} batches into {len(panel):,} rows: {output}")


if __name__ == "__main__":
    main()
