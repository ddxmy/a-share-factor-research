#!/usr/bin/env python3
"""Assemble v2 campaign metrics and separate provisional library artifacts."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "skills" / "a-share-factor-miner" / "scripts"))

from quality_score import load_config, score_band, score_record  # noqa: E402


def json_value(value: Any) -> Any:
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-summary", required=True)
    parser.add_argument("--csi500-summary", required=True)
    parser.add_argument("--liquid-summary", required=True)
    parser.add_argument("--correlations", required=True)
    parser.add_argument("--economic-review", required=True)
    parser.add_argument("--freeze-manifest", required=True)
    parser.add_argument("--legacy-summary", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    libraries_dir = output_dir / "libraries"
    libraries_dir.mkdir()

    base = pd.read_csv(args.base_summary).set_index("factor_id")
    csi = pd.read_csv(args.csi500_summary).set_index("factor_id")
    liquid = pd.read_csv(args.liquid_summary).set_index("factor_id")
    correlations = pd.read_csv(args.correlations)
    reviews = json.loads(Path(args.economic_review).read_text(encoding="utf-8"))["reviews"]
    freeze = json.loads(Path(args.freeze_manifest).read_text(encoding="utf-8"))
    frozen = {item["factor_id"]: item for item in freeze["frozen_candidates"]}
    legacy = pd.read_csv(args.legacy_summary).set_index("factor_id")
    if set(base.index) != set(frozen) or set(base.index) != set(reviews):
        raise RuntimeError("Frozen, validated, and economic-review factor sets differ")

    legacy_ids = {f"xzt_20260707_{number}" for number in range(1, 5)}
    pairs = correlations.loc[
        (
            correlations["left_factor_id"].isin(base.index)
            & correlations["right_factor_id"].isin(legacy_ids)
        )
        | (
            correlations["right_factor_id"].isin(base.index)
            & correlations["left_factor_id"].isin(legacy_ids)
        )
    ].copy()
    pairs["factor_id"] = pairs["left_factor_id"].where(
        pairs["left_factor_id"].isin(base.index), pairs["right_factor_id"]
    )
    pairs["legacy_factor"] = pairs["right_factor_id"].where(
        pairs["left_factor_id"].isin(base.index), pairs["left_factor_id"]
    )
    best = pairs.loc[pairs.groupby("factor_id")["average_abs_daily_spearman"].idxmax()].set_index(
        "factor_id"
    )

    config = load_config()
    rows: list[dict[str, Any]] = []
    score_details: dict[str, Any] = {}
    for factor_id, row in base.iterrows():
        metrics = row.to_dict()
        metrics.update(
            {
                "csi500_rank_ic": float(csi.loc[factor_id, "transfer_validation_rank_ic"]),
                "liquid_all_a_rank_ic": float(
                    liquid.loc[factor_id, "transfer_validation_rank_ic"]
                ),
                "max_abs_library_correlation": float(
                    best.loc[factor_id, "average_abs_daily_spearman"]
                ),
            }
        )
        # Intentionally omit parameter_stability: no grid was frozen before validation.
        score = score_record(metrics, config)
        score_details[factor_id] = score
        legacy_factor = str(best.loc[factor_id, "legacy_factor"])
        legacy_row = legacy.loc[legacy_factor]
        base_failures = [] if pd.isna(row["hard_gate_failures"]) else str(
            row["hard_gate_failures"]
        ).split(",")
        if metrics["csi500_rank_ic"] < 0:
            base_failures.append("csi500_transfer")
        if metrics["liquid_all_a_rank_ic"] < 0:
            base_failures.append("liquid_all_a_transfer")
        review = reviews[factor_id]
        if review["economic_gate"] == "FAIL":
            base_failures.append("economic_gate")
        rows.append(
            {
                "factor_id": factor_id,
                "factor_name": row["factor_name"],
                "economic_family": row["economic_family"],
                "discovery_rank_ic": row["discovery_rank_ic"],
                "validation_rank_ic": row["validation_rank_ic"],
                "newey_west_t": row["newey_west_t"],
                "global_fdr_q": row["fdr_q"],
                "net_sharpe_10bps": row["net_sharpe_10bps"],
                "net_sharpe_20bps": row["net_20bps_annualized_sharpe"],
                "average_daily_turnover": row["average_daily_turnover"],
                "csi500_rank_ic": metrics["csi500_rank_ic"],
                "liquid_all_a_rank_ic": metrics["liquid_all_a_rank_ic"],
                "max_abs_legacy_correlation": metrics["max_abs_library_correlation"],
                "best_legacy_match": legacy_factor,
                "validation_ic_improvement_vs_legacy": (
                    row["validation_rank_ic"] / legacy_row["validation_rank_ic"] - 1
                    if legacy_row["validation_rank_ic"] > 0
                    else None
                ),
                "partial_score_improvement_vs_legacy": (
                    row["normalized_observed_score"]
                    - legacy_row["normalized_observed_score"]
                ),
                "parameter_audit": "missing_preregistered_grid",
                "score_available_weight": score["available_weight"],
                "score_completeness": score["score_completeness"],
                "provisional_composite_score": score["normalized_observed_score"],
                "provisional_band": score_band(score["normalized_observed_score"], config),
                "hard_gate_failures_after_transfer": ",".join(dict.fromkeys(base_failures)),
                "economic_gate": review["economic_gate"],
                "library_decision": review["decision"],
                "decision_reason": review["reason"],
                "formal_admission": False,
            }
        )

    summary = pd.DataFrame(rows).sort_values(
        ["library_decision", "validation_rank_ic"], ascending=[True, False]
    )
    summary.to_csv(output_dir / "complete_factor_summary.csv", index=False)
    (output_dir / "score_details.json").write_text(
        json.dumps(score_details, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    def library_payload(kind: str, decisions: set[str]) -> dict[str, Any]:
        selected = summary.loc[summary["library_decision"].isin(decisions)]
        factors = []
        for _, item in selected.iterrows():
            record = frozen[item["factor_id"]]
            factors.append(
                {
                    **record,
                    "validation_rank_ic": json_value(item["validation_rank_ic"]),
                    "csi500_rank_ic": json_value(item["csi500_rank_ic"]),
                    "liquid_all_a_rank_ic": json_value(item["liquid_all_a_rank_ic"]),
                    "net_sharpe_10bps": json_value(item["net_sharpe_10bps"]),
                    "net_sharpe_20bps": json_value(item["net_sharpe_20bps"]),
                    "max_abs_legacy_correlation": json_value(
                        item["max_abs_legacy_correlation"]
                    ),
                    "library_decision": item["library_decision"],
                }
            )
        return {
            "campaign_version": freeze["campaign_version"],
            "formula_set_hash": freeze["formula_set_hash"],
            "library_kind": kind,
            "status": "provisional_no_formal_admission",
            "contains_only_local_factors": True,
            "blocking_audits": [
                "parameter grid was not pre-registered before factor validation",
                "score config remains provisional",
            ],
            "factor_count": len(factors),
            "factors": factors,
        }

    research_decisions = {
        "predictive_replacement_candidate",
        "independent_predictive_and_tradable_candidate",
        "research_library",
    }
    predictive_decisions = {
        "predictive_replacement_candidate",
        "independent_predictive_and_tradable_candidate",
    }
    tradable_decisions = {"independent_predictive_and_tradable_candidate"}
    (libraries_dir / "research_library.json").write_text(
        json.dumps(library_payload("research_library", research_decisions), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (libraries_dir / "predictive_core_candidates.json").write_text(
        json.dumps(
            library_payload("predictive_core_candidates", predictive_decisions),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (libraries_dir / "tradable_core_candidates.json").write_text(
        json.dumps(
            library_payload("tradable_core_candidates", tradable_decisions),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    benchmark = {
        "library_kind": "benchmark_control_library",
        "status": "incomplete_pending_alpha158_and_fixed_controls",
        "contains_local_admissions": False,
        "legacy_factorminer": sorted(legacy_ids),
        "alpha158": {"status": "pending_construction", "factors": []},
        "classic_controls": {"status": "pending_freeze", "factors": []},
        "random_and_invalid_controls": {"status": "pending_freeze", "factors": []},
        "comparison_matrix": [
            "local predictive core",
            "local tradable core",
            "legacy FactorMiner",
            "Alpha158",
            "local predictive core + Alpha158",
            "classic controls",
        ],
    }
    (libraries_dir / "benchmark_control_library.json").write_text(
        json.dumps(benchmark, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    report_lines = [
        "# Local Ralph v2 campaign review",
        "",
        f"- Proposals: 120; discovery-eligible: 42; globally frozen: {len(base)}",
        f"- Formula set hash: `{freeze['formula_set_hash']}`",
        "- Factor validation: 2021–2022; directions frozen on 2016–2020",
        "- Transfers: dynamic CSI500 and point-in-time liquid all-A top 1000",
        "- Formal admission: **blocked** because the parameter grid was not frozen before validation and the score config is provisional",
        "",
        "| Factor | Decision | HS300 IC | CSI500 IC | Liquid A IC | Net10 | Net20 | Legacy corr | Partial score |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    shown = summary.loc[summary["library_decision"].ne("trajectory_only")]
    for _, item in shown.iterrows():
        report_lines.append(
            f"| {item['factor_name']} | {item['library_decision']} | "
            f"{item['validation_rank_ic']:.4f} | {item['csi500_rank_ic']:.4f} | "
            f"{item['liquid_all_a_rank_ic']:.4f} | {item['net_sharpe_10bps']:.2f} | "
            f"{item['net_sharpe_20bps']:.2f} | {item['max_abs_legacy_correlation']:.3f} | "
            f"{item['provisional_composite_score']:.2f} |"
        )
    report_lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The two strongest predictive signals are improvements within existing price/turnover clusters; they are provisional replacement candidates, not independent new families.",
            "- Tail-risk Damped Overnight Drift is the only candidate that currently combines statistical gates, transfer robustness, low legacy correlation, and positive 10/20 bps cost stress.",
            "- Downside Tail Volume Pressure is retained for research because its validation was strong but its discovery IC missed the pre-registered core threshold.",
            "- Failed and invalid proposals remain in the 120-record trajectory and are not silently removed from campaign yield reporting.",
            "",
            "## Library comparison design",
            "",
            "Local factors are stored only in the local research/predictive/tradable artifacts. Legacy FactorMiner, Alpha158, classic factors, random controls, and invalid controls remain in a separate benchmark library. This makes A/B comparisons possible without contaminating local admission decisions.",
        ]
    )
    (output_dir / "campaign_review.md").write_text(
        "\n".join(report_lines) + "\n", encoding="utf-8"
    )
    run_manifest = {
        "campaign_version": freeze["campaign_version"],
        "formula_set_hash": freeze["formula_set_hash"],
        "status": "campaign_review_complete_formal_admission_blocked",
        "validation_labels_opened": True,
        "generation_may_resume": False,
        "synthesis_validation_opened": False,
        "lockbox_opened": False,
        "formal_admission": False,
        "research_library_count": len(
            summary.loc[summary["library_decision"].isin(research_decisions)]
        ),
        "predictive_core_candidate_count": len(
            summary.loc[summary["library_decision"].isin(predictive_decisions)]
        ),
        "tradable_core_candidate_count": len(
            summary.loc[summary["library_decision"].isin(tradable_decisions)]
        ),
    }
    (output_dir / "run_manifest.json").write_text(
        json.dumps(run_manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(run_manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
