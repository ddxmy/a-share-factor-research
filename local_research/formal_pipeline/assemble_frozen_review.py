#!/usr/bin/env python3
"""Assemble complete metrics, score components, decisions, and review text."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SKILL_SCRIPTS = PROJECT_ROOT / "skills" / "a-share-factor-miner" / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))

from quality_score import load_config, score_band, score_record  # noqa: E402


def safe(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-summary", required=True)
    parser.add_argument("--csi500-summary", required=True)
    parser.add_argument("--liquid-summary", required=True)
    parser.add_argument("--parameter-summary", required=True)
    parser.add_argument("--correlations", required=True)
    parser.add_argument("--economic-review", required=True)
    parser.add_argument("--frozen-manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    base = pd.read_csv(args.base_summary).set_index("factor_id")
    csi = pd.read_csv(args.csi500_summary).set_index("factor_id")
    liquid = pd.read_csv(args.liquid_summary).set_index("factor_id")
    params = pd.read_csv(args.parameter_summary).set_index("factor_id")
    correlations = pd.read_csv(args.correlations)
    economic = json.loads(Path(args.economic_review).read_text(encoding="utf-8"))["reviews"]
    frozen = json.loads(Path(args.frozen_manifest).read_text(encoding="utf-8"))
    frozen_records = {item["factor_id"]: item for item in frozen["candidates"]}

    new_ids = set(base.index)
    legacy_ids = {f"xzt_20260707_{number}" for number in range(1, 5)}
    library_pairs = correlations.loc[
        (
            correlations["left_factor_id"].isin(new_ids)
            & correlations["right_factor_id"].isin(legacy_ids)
        )
        | (
            correlations["right_factor_id"].isin(new_ids)
            & correlations["left_factor_id"].isin(legacy_ids)
        )
    ].copy()
    library_pairs["factor_id"] = library_pairs["left_factor_id"].where(
        library_pairs["left_factor_id"].isin(new_ids), library_pairs["right_factor_id"]
    )
    library_pairs["library_factor"] = library_pairs["right_factor_id"].where(
        library_pairs["left_factor_id"].isin(new_ids), library_pairs["left_factor_id"]
    )
    best_matches = library_pairs.loc[
        library_pairs.groupby("factor_id")["average_abs_daily_spearman"].idxmax()
    ].set_index("factor_id")

    config = load_config()
    summary_rows: list[dict[str, Any]] = []
    score_details: dict[str, Any] = {}
    trajectory: list[dict[str, Any]] = []
    for factor_id, row in base.iterrows():
        metrics = row.to_dict()
        metrics.update(
            {
                "parameter_stability": float(params.loc[factor_id, "parameter_stability"]),
                "csi500_rank_ic": float(csi.loc[factor_id, "transfer_validation_rank_ic"]),
                "liquid_all_a_rank_ic": float(
                    liquid.loc[factor_id, "transfer_validation_rank_ic"]
                ),
                "max_abs_library_correlation": float(
                    best_matches.loc[factor_id, "average_abs_daily_spearman"]
                ),
            }
        )
        score = score_record(metrics, config)
        score_details[factor_id] = score
        quality = score["formal_quality_score"]
        review = economic[factor_id]
        hard_failures = [] if pd.isna(row["hard_gate_failures"]) else str(
            row["hard_gate_failures"]
        ).split(",")
        summary_row = {
            "factor_id": factor_id,
            "formula": frozen_records[factor_id]["formula"],
            "train_direction": int(frozen_records[factor_id]["train_direction"]),
            "discovery_rank_ic": float(row["discovery_rank_ic"]),
            "validation_rank_ic": float(row["validation_rank_ic"]),
            "newey_west_t": float(row["newey_west_t"]),
            "fdr_q": float(row["fdr_q"]),
            "net_sharpe_10bps": float(row["net_sharpe_10bps"]),
            "average_daily_turnover": float(row["average_daily_turnover"]),
            "csi500_rank_ic": metrics["csi500_rank_ic"],
            "liquid_all_a_rank_ic": metrics["liquid_all_a_rank_ic"],
            "parameter_stability": metrics["parameter_stability"],
            "max_abs_library_correlation": metrics["max_abs_library_correlation"],
            "best_library_match": str(best_matches.loc[factor_id, "library_factor"]),
            "quality_score": quality,
            "score_band": score_band(quality, config) if quality is not None else None,
            "score_config_status": config["status"],
            "hard_gate_failures": ",".join(hard_failures),
            "economic_gate": review["economic_gate"],
            "decision": review["decision"],
            "decision_reason": review["reason"],
        }
        summary_rows.append(summary_row)
        trajectory.append(
            {
                **frozen_records[factor_id],
                "experiment_version": frozen["experiment_version"],
                "stage": "factor_validation_complete_metrics",
                "status": review["decision"],
                "hard_gate_failures": hard_failures,
                "economic_gate": review["economic_gate"],
                "decision_reason": review["reason"],
                "metrics": {key: safe(value) for key, value in metrics.items()},
                "score": score,
            }
        )

    summary = pd.DataFrame(summary_rows).sort_values(
        ["quality_score", "validation_rank_ic"], ascending=[False, False], na_position="last"
    )
    summary.to_csv(output_dir / "complete_factor_summary.csv", index=False)
    (output_dir / "score_components.json").write_text(
        json.dumps(score_details, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "validation_trajectory.jsonl").write_text(
        "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in trajectory),
        encoding="utf-8",
    )

    lines = [
        "# Local Ralph v1 complete factor review",
        "",
        f"- Formula set hash: `{frozen['formula_set_hash']}`",
        f"- Score version: `{config['version']}`",
        f"- Score config status: `{config['status']}`",
        "- Validation: 2021–2022; directions frozen on 2016–2020",
        "- Transfers: CSI 500 and point-in-time liquid all-A top 1,000",
        "",
        "The 100-point metric vector is complete, but admission remains blocked until the evaluator's fixed control calibration changes the score config from provisional to frozen.",
        "",
        "| Factor | Score | Band | HS300 IC | NW t | Net Sharpe 10bps | CSI500 IC | Liquid All-A IC | Turnover | Max legacy corr | Decision |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for _, item in summary.iterrows():
        score_text = "NA" if pd.isna(item["quality_score"]) else f"{item['quality_score']:.2f}"
        lines.append(
            f"| {item['factor_id']} | {score_text} | {item['score_band'] or 'NA'} | "
            f"{item['validation_rank_ic']:.4f} | {item['newey_west_t']:.2f} | "
            f"{item['net_sharpe_10bps']:.2f} | {item['csi500_rank_ic']:.4f} | "
            f"{item['liquid_all_a_rank_ic']:.4f} | {item['average_daily_turnover']:.3f} | "
            f"{item['max_abs_library_correlation']:.3f} | {item['decision']} |"
        )
    lines.extend(["", "## Economic decisions", ""])
    for _, item in summary.iterrows():
        lines.append(
            f"- `{item['factor_id']}` — **{item['economic_gate']} / {item['decision']}**: "
            f"{item['decision_reason']}"
        )
    (output_dir / "complete_review.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(summary[["factor_id", "quality_score", "score_band", "decision"]].to_string(index=False))
    print(f"Saved complete review to {output_dir}")


if __name__ == "__main__":
    main()
