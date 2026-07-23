#!/usr/bin/env python3
"""Evaluate a frozen factor batch on a transfer universe without reorienting signals."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from evaluate_factors import (
    PROJECT_ROOT,
    FormulaExecutor,
    daily_ic,
    halfyear_statistics,
    load_factor_records,
    load_panel,
    portfolio_diagnostics,
    preprocess_signal,
)
from calibrate_scores import bh_qvalues, newey_west_t


DISCOVERY_START = pd.Timestamp("2016-01-01")
DISCOVERY_END = pd.Timestamp("2020-12-31")
VALIDATION_START = pd.Timestamp("2021-01-01")
VALIDATION_END = pd.Timestamp("2022-12-31")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", required=True)
    parser.add_argument("--frozen-manifest", required=True)
    parser.add_argument("--campaign-manifest", required=True)
    parser.add_argument("--script-version", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    panel_path = Path(args.panel).resolve()
    panel_manifest = json.loads(
        panel_path.with_suffix(".manifest.json").read_text(encoding="utf-8")
    )
    frozen_path = Path(args.frozen_manifest).resolve()
    frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
    campaign_path = Path(args.campaign_manifest).resolve()
    campaign = json.loads(campaign_path.read_text(encoding="utf-8"))
    if frozen.get("status") != "formula_frozen_validation_sealed":
        raise RuntimeError("Formula set is not frozen")
    if campaign.get("campaign_hash") != frozen.get("campaign_hash"):
        raise RuntimeError("Campaign and frozen formula-set hashes differ")
    if panel_manifest.get("research_stage") != "factor_validation":
        raise RuntimeError("Transfer evaluator requires a factor_validation panel")
    if panel_manifest.get("output_sha256") != sha256_file(panel_path):
        raise RuntimeError("Transfer panel hash differs from its manifest")
    if panel_manifest.get("data_snapshot") != campaign["data_snapshot"]:
        raise RuntimeError("Transfer data snapshot differs from the frozen campaign")
    if panel_manifest.get("label_version") != campaign["label_version"]:
        raise RuntimeError("Transfer label version differs from the frozen campaign")
    frozen_candidates = frozen.get("frozen_candidates", frozen.get("candidates"))
    if not frozen_candidates:
        raise RuntimeError("Frozen manifest has no candidates")
    frozen_records = {item["factor_id"]: item for item in frozen_candidates}
    active_records = {
        item["factor_id"]: item
        for item in load_factor_records(PROJECT_ROOT / "factor_script" / args.script_version)
        if item["factor_id"] in frozen_records
    }
    if set(active_records) != set(frozen_records):
        raise RuntimeError("Frozen factor scripts are missing or duplicated")
    for factor_id, record in active_records.items():
        expected = frozen_records[factor_id]["formula_hash"]
        actual = hashlib.sha256(record["formula"].encode("utf-8")).hexdigest()
        if actual != expected:
            raise RuntimeError(f"Formula hash changed after freeze: {factor_id}")

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    metadata = load_panel(panel_path)
    executor = FormulaExecutor(str(panel_path), start_date=20150101, end_date=20221231)
    results: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []

    for position, factor_id in enumerate(frozen_records, start=1):
        record = active_records[factor_id]
        direction = int(frozen_records[factor_id]["train_direction"])
        try:
            prepared = preprocess_signal(executor.compute(record["formula"]), metadata)
            evaluable = prepared.loc[prepared["primary_evaluable"]]
            dates = evaluable.index.get_level_values("dt")
            discovery = evaluable.loc[(dates >= DISCOVERY_START) & (dates <= DISCOVERY_END)]
            validation = evaluable.loc[(dates >= VALIDATION_START) & (dates <= VALIDATION_END)]
            discovery_ic = direction * daily_ic(
                discovery, "neutral_signal", "next_open_to_close"
            )
            validation_ic = direction * daily_ic(
                validation, "neutral_signal", "next_open_to_close"
            )
            validation_raw_ic = direction * daily_ic(
                validation, "raw_signal", "next_open_to_close"
            )
            secondary_ic = direction * daily_ic(
                validation, "neutral_signal", "next_close_to_close"
            )
            half_ratio, worst_half, half_count = halfyear_statistics(validation_ic)
            nw_t, one_sided_p, nw_lag = newey_west_t(validation_ic)
            portfolio, daily_portfolio = portfolio_diagnostics(validation, direction)
            eligible_counts = metadata.loc[metadata["primary_evaluable"]].groupby(level="dt").size()
            factor_counts = prepared.loc[
                prepared["primary_evaluable"] & prepared["neutral_signal"].notna()
            ].groupby(level="dt").size()
            coverage = factor_counts / eligible_counts.reindex(factor_counts.index)
            raw_abs = abs(float(validation_raw_ic.mean()))
            result = {
                **record,
                "frozen_train_direction": direction,
                "transfer_discovery_rank_ic": float(discovery_ic.mean()),
                "transfer_validation_rank_ic": float(validation_ic.mean()),
                "transfer_validation_icir": float(
                    validation_ic.mean() / (validation_ic.std(ddof=1) + 1e-12)
                ),
                "transfer_positive_halfyear_ratio": half_ratio,
                "transfer_worst_halfyear_ic": worst_half,
                "transfer_halfyear_count": half_count,
                "transfer_newey_west_t": float(nw_t),
                "one_sided_p": float(one_sided_p),
                "newey_west_lag": int(nw_lag),
                "transfer_neutralization_retention": (
                    abs(float(validation_ic.mean())) / raw_abs if raw_abs > 1e-12 else np.nan
                ),
                "transfer_secondary_label_rank_ic": float(secondary_ic.mean()),
                "average_signal_coverage": float(coverage.mean()),
                **portfolio,
            }
            results.append(result)
            pd.DataFrame(
                {
                    "transfer_validation_ic": validation_ic,
                    "transfer_secondary_ic": secondary_ic,
                }
            ).join(daily_portfolio, how="outer").to_parquet(
                output_dir / f"factor_{factor_id}_transfer_daily.parquet"
            )
            print(
                f"[{position}/{len(frozen_records)}] {factor_id}: "
                f"direction={direction:+d} transfer_IC={validation_ic.mean():.4f}",
                flush=True,
            )
        except Exception as exc:
            failures.append({**record, "error": str(exc)})
            print(f"[{position}/{len(frozen_records)}] {factor_id}: FAILED {exc}", flush=True)

    summary = pd.DataFrame(results)
    if not summary.empty:
        summary["transfer_fdr_q"] = bh_qvalues(summary["one_sided_p"])
        summary["passes_nonnegative_transfer_gate"] = summary[
            "transfer_validation_rank_ic"
        ].ge(0)
        summary.sort_values("transfer_validation_rank_ic", ascending=False).to_csv(
            output_dir / "transfer_summary.csv", index=False
        )
    (output_dir / "failures.json").write_text(
        json.dumps(failures, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    run_manifest = {
        "created_at": pd.Timestamp.now(tz="Asia/Shanghai").isoformat(),
        "stage": "factor_validation_transfer",
        "universe_code": panel_manifest["universe_code"],
        "data_snapshot": panel_manifest["data_snapshot"],
        "panel_sha256": panel_manifest["output_sha256"],
        "formula_set_hash": frozen["formula_set_hash"],
        "campaign_hash": campaign["campaign_hash"],
        "campaign_manifest": str(campaign_path),
        "campaign_manifest_sha256": sha256_file(campaign_path),
        "direction_source": str(frozen_path),
        "frozen_manifest_sha256": sha256_file(frozen_path),
        "script_version": args.script_version,
        "directions_reestimated_on_transfer": False,
        "validation_labels_opened": True,
        "generation_may_resume": False,
        "completed": len(results),
        "failed": len(failures),
    }
    (output_dir / "run_manifest.json").write_text(
        json.dumps(run_manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Saved frozen transfer evaluation to {output_dir}")


if __name__ == "__main__":
    main()
