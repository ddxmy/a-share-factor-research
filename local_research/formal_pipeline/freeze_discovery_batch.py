#!/usr/bin/env python3
"""Freeze a discovery batch and create an append-only local candidate trajectory."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def script_metadata(factor_id: str) -> dict[str, Any]:
    matches = list((PROJECT_ROOT / "factor_script").rglob(f"{factor_id}.py"))
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one script for {factor_id}, found {matches}")
    path = matches[0]
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    values: dict[str, Any] = {}
    for node in tree.body:
        if not (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        ):
            continue
        try:
            values[node.targets[0].id] = ast.literal_eval(node.value)
        except Exception:
            continue
    formula = str(values["FORMULA"])
    return {
        "factor_id": factor_id,
        "factor_name": str(values["FACTOR_NAME"]),
        "formula": formula,
        "formula_hash": hashlib.sha256(formula.encode("utf-8")).hexdigest(),
        "economic_hypothesis": values.get("ECONOMIC_HYPOTHESIS"),
        "target_patterns": str(values.get("TARGET_PATTERNS", "")).split(","),
        "script_path": str(path.relative_to(PROJECT_ROOT)),
    }


def json_safe(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all-summary", action="append", required=True)
    parser.add_argument("--frozen-summary", required=True)
    parser.add_argument("--factor", action="append", required=True)
    parser.add_argument("--panel-manifest", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--trajectory", required=True)
    args = parser.parse_args()

    output = Path(args.output).resolve()
    trajectory = Path(args.trajectory).resolve()
    if output.exists() or trajectory.exists():
        raise FileExistsError("Freeze outputs are immutable; choose new paths")

    panel_manifest = json.loads(Path(args.panel_manifest).read_text(encoding="utf-8"))
    frozen_summary = pd.read_csv(args.frozen_summary).set_index("factor_id")
    selected = list(dict.fromkeys(args.factor))
    candidates: list[dict[str, Any]] = []
    for factor_id in selected:
        row = frozen_summary.loc[factor_id]
        candidates.append(
            {
                **script_metadata(factor_id),
                "train_direction": int(row["train_direction"]),
                "discovery_rank_ic": float(row["discovery_rank_ic"]),
                "discovery_newey_west_t": float(row["newey_west_t"]),
                "discovery_bh_q": float(row["discovery_bh_q"]),
                "discovery_net_sharpe_10bps": float(row["net_sharpe_10bps"]),
                "discovery_average_daily_turnover": float(row["average_daily_turnover"]),
                "discovery_screen_failures": (
                    []
                    if pd.isna(row["discovery_screen_failures"])
                    else str(row["discovery_screen_failures"]).split(",")
                ),
                "freeze_status": "frozen_for_factor_validation",
            }
        )

    formula_set_hash = hashlib.sha256(
        "\n".join(sorted(item["formula_hash"] for item in candidates)).encode("utf-8")
    ).hexdigest()
    manifest = {
        "experiment_version": "local_ralph_20260719_v1",
        "created_at": pd.Timestamp.now(tz="Asia/Shanghai").isoformat(),
        "formula_generation_closed": True,
        "validation_opened_at_freeze": False,
        "resume_mining_after_validation_allowed": False,
        "evaluator_version": "hs300_daily_evaluator_v1",
        "data_snapshot": panel_manifest["data_snapshot"],
        "panel_sha256": panel_manifest["output_sha256"],
        "universe_version": panel_manifest["universe_sha256"],
        "label_version": panel_manifest["label_version"],
        "discovery_period": ["2016-01-01", "2020-12-31"],
        "factor_validation_period": ["2021-01-01", "2022-12-31"],
        "formula_set_hash": formula_set_hash,
        "candidate_count": len(candidates),
        "candidates": candidates,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    records: list[dict[str, Any]] = []
    selected_set = set(selected)
    for summary_path in args.all_summary:
        summary = pd.read_csv(summary_path)
        for _, row in summary.iterrows():
            factor_id = str(row["factor_id"])
            failures = (
                []
                if pd.isna(row["discovery_screen_failures"])
                else str(row["discovery_screen_failures"]).split(",")
            )
            status = "frozen_for_factor_validation" if factor_id in selected_set else (
                "discovery_screen_pass_not_selected"
                if bool(row["passes_discovery_screen"])
                else "discovery_fail"
            )
            metrics = {
                key: json_safe(row[key])
                for key in [
                    "train_direction",
                    "discovery_rank_ic",
                    "discovery_raw_rank_ic",
                    "discovery_icir",
                    "monthly_ic_hit_rate",
                    "positive_halfyear_ratio",
                    "worst_halfyear_ic",
                    "newey_west_t",
                    "discovery_bh_q",
                    "neutralization_retention",
                    "net_sharpe_10bps",
                    "net_20bps_annualized_sharpe",
                    "average_daily_turnover",
                    "average_signal_coverage",
                ]
            }
            records.append(
                {
                    **script_metadata(factor_id),
                    "experiment_version": manifest["experiment_version"],
                    "evaluator_version": manifest["evaluator_version"],
                    "data_snapshot": manifest["data_snapshot"],
                    "stage": "discovery",
                    "status": status,
                    "hard_gate_failures": failures,
                    "metrics": metrics,
                }
            )
    trajectory.parent.mkdir(parents=True, exist_ok=True)
    trajectory.write_text(
        "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )
    print(f"Frozen {len(candidates)} candidates: {formula_set_hash}")
    print(f"Recorded {len(records)} discovery outcomes: {trajectory}")


if __name__ == "__main__":
    main()
