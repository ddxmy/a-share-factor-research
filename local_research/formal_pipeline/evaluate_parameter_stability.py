#!/usr/bin/env python3
"""Evaluate a predeclared parameter grid using frozen discovery directions."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from evaluate_factors import FormulaExecutor, daily_ic, load_panel, preprocess_signal


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
    parser.add_argument("--parameter-grid", required=True)
    parser.add_argument("--base-summary", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    panel_path = Path(args.panel).resolve()
    panel_manifest = json.loads(
        panel_path.with_suffix(".manifest.json").read_text(encoding="utf-8")
    )
    frozen = json.loads(Path(args.frozen_manifest).read_text(encoding="utf-8"))
    campaign = json.loads(Path(args.campaign_manifest).read_text(encoding="utf-8"))
    grid_path = Path(args.parameter_grid).resolve()
    grid_bytes = grid_path.read_bytes()
    grid = json.loads(grid_bytes)
    if frozen.get("status") != "formula_frozen_validation_sealed":
        raise RuntimeError("Formula set is not frozen")
    if campaign.get("campaign_hash") != frozen.get("campaign_hash"):
        raise RuntimeError("Campaign and frozen formula-set hashes differ")
    if grid.get("campaign_hash") != frozen.get("campaign_hash"):
        raise RuntimeError("Parameter plan and frozen formula-set hashes differ")
    if hashlib.sha256(grid_bytes).hexdigest() != frozen.get("parameter_plan_sha256"):
        raise RuntimeError("Parameter plan changed after formula freeze")
    if panel_manifest.get("research_stage") != "factor_validation":
        raise RuntimeError("Parameter stability requires a factor_validation panel")
    if panel_manifest.get("output_sha256") != sha256_file(panel_path):
        raise RuntimeError("Parameter panel hash differs from its manifest")
    expected_panel_identity = {
        "data_snapshot": campaign["data_snapshot"],
        "label_version": campaign["label_version"],
        "universe_sha256": campaign["universe_version"],
    }
    mismatches = {
        key: (panel_manifest.get(key), value)
        for key, value in expected_panel_identity.items()
        if panel_manifest.get(key) != value
    }
    if mismatches:
        raise RuntimeError(f"Parameter panel identity mismatch: {mismatches}")
    frozen_records = {item["factor_id"]: item for item in frozen["frozen_candidates"]}
    plan_rows = grid.get("parameter_plans", [])
    plans = {str(item.get("candidate_id")): item for item in plan_rows}
    if len(plans) != len(plan_rows) or not set(frozen_records).issubset(plans):
        raise RuntimeError("Parameter plan must cover every frozen factor exactly once")

    base = pd.read_csv(args.base_summary).set_index("factor_id")
    if set(base.index) != set(frozen_records):
        raise RuntimeError("Base validation summary and frozen factor set differ")
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    metadata = load_panel(panel_path)
    executor = FormulaExecutor(str(panel_path), start_date=20150101, end_date=20221231)
    dates = metadata.index.get_level_values("dt")
    validation_metadata = metadata.loc[
        (dates >= VALIDATION_START) & (dates <= VALIDATION_END)
    ]

    variant_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    for factor_id in frozen_records:
        specification = plans[factor_id]
        direction = int(frozen_records[factor_id]["train_direction"])
        base_ic = float(base.loc[factor_id, "validation_rank_ic"])
        if specification["parameter_free"]:
            summary_rows.append(
                {
                    "factor_id": factor_id,
                    "parameter_free": True,
                    "variant_count": 0,
                    "stable_variant_count": 0,
                    "parameter_stability": 1.0,
                    "base_validation_rank_ic": base_ic,
                }
            )
            continue

        stable_count = 0
        variants = specification["formula_variants"]
        for variant in variants:
            prepared = preprocess_signal(executor.compute(variant["formula"]), validation_metadata)
            evaluable = prepared.loc[prepared["primary_evaluable"]]
            oriented = direction * daily_ic(
                evaluable, "neutral_signal", "next_open_to_close"
            )
            variant_ic = float(oriented.mean())
            retention = variant_ic / base_ic if base_ic > 0 else float("nan")
            stable = bool(variant_ic > 0 and retention >= 0.50)
            stable_count += int(stable)
            variant_rows.append(
                {
                    "factor_id": factor_id,
                    "variant": variant["variant_name"],
                    "formula": variant["formula"],
                    "frozen_direction": direction,
                    "base_validation_rank_ic": base_ic,
                    "variant_validation_rank_ic": variant_ic,
                    "ic_retention": retention,
                    "stable": stable,
                }
            )
            print(
                f"{factor_id} {variant['variant_name']}: IC={variant_ic:.4f} "
                f"retention={retention:.2%} stable={stable}",
                flush=True,
            )
        summary_rows.append(
            {
                "factor_id": factor_id,
                "parameter_free": False,
                "variant_count": len(variants),
                "stable_variant_count": stable_count,
                "parameter_stability": stable_count / len(variants),
                "base_validation_rank_ic": base_ic,
            }
        )

    pd.DataFrame(variant_rows).to_csv(output_dir / "parameter_variants.csv", index=False)
    pd.DataFrame(summary_rows).sort_values(
        ["parameter_stability", "base_validation_rank_ic"], ascending=[False, False]
    ).to_csv(output_dir / "parameter_stability_summary.csv", index=False)
    manifest = {
        "created_at": pd.Timestamp.now(tz="Asia/Shanghai").isoformat(),
        "stage": "factor_validation_parameter_stability",
        "formula_set_hash": frozen["formula_set_hash"],
        "parameter_grid": str(grid_path),
        "parameter_grid_sha256": hashlib.sha256(grid_bytes).hexdigest(),
        "campaign_hash": campaign["campaign_hash"],
        "panel_sha256": panel_manifest["output_sha256"],
        "direction_source": str(Path(args.frozen_manifest).resolve()),
        "directions_reestimated": False,
        "stability_rule": "variant validation IC > 0 and >= 50% of frozen base validation IC",
        "validation_labels_opened": True,
        "generation_may_resume": False,
    }
    (output_dir / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Saved parameter stability evaluation to {output_dir}")


if __name__ == "__main__":
    main()
