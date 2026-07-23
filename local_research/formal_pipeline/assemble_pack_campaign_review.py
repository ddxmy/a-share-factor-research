#!/usr/bin/env python3
"""Assemble complete Pack-40 campaign scores, decisions, and library artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "skills" / "a-share-factor-miner" / "scripts"))

from quality_score import load_config, score_band, score_record  # noqa: E402

from evaluate_factors import hard_gate_failures  # noqa: E402


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_value(value: Any) -> Any:
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def write_json_exclusive(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-summary", required=True)
    parser.add_argument("--csi500-summary", required=True)
    parser.add_argument("--liquid-summary", required=True)
    parser.add_argument("--parameter-summary", required=True)
    parser.add_argument("--library-summary", required=True)
    parser.add_argument("--library-pairs", required=True)
    parser.add_argument("--economic-review", required=True)
    parser.add_argument("--freeze-manifest", required=True)
    parser.add_argument("--campaign-manifest", required=True)
    parser.add_argument("--prior-complete-summary", required=True)
    parser.add_argument("--library-index", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    input_paths = {
        name: Path(value).resolve()
        for name, value in {
            "base_summary": args.base_summary,
            "csi500_summary": args.csi500_summary,
            "liquid_summary": args.liquid_summary,
            "parameter_summary": args.parameter_summary,
            "library_summary": args.library_summary,
            "library_pairs": args.library_pairs,
            "economic_review": args.economic_review,
            "freeze_manifest": args.freeze_manifest,
            "campaign_manifest": args.campaign_manifest,
            "prior_complete_summary": args.prior_complete_summary,
            "library_index": args.library_index,
        }.items()
    }
    for path in input_paths.values():
        if not path.exists():
            raise FileNotFoundError(path)

    base = pd.read_csv(input_paths["base_summary"]).set_index("factor_id")
    csi = pd.read_csv(input_paths["csi500_summary"]).set_index("factor_id")
    liquid = pd.read_csv(input_paths["liquid_summary"]).set_index("factor_id")
    params = pd.read_csv(input_paths["parameter_summary"]).set_index("factor_id")
    library = pd.read_csv(input_paths["library_summary"]).set_index("factor_id")
    pairs = pd.read_csv(input_paths["library_pairs"])
    economics_payload = json.loads(input_paths["economic_review"].read_text(encoding="utf-8"))
    economics = economics_payload["reviews"]
    freeze = json.loads(input_paths["freeze_manifest"].read_text(encoding="utf-8"))
    campaign = json.loads(input_paths["campaign_manifest"].read_text(encoding="utf-8"))
    prior = pd.read_csv(input_paths["prior_complete_summary"]).set_index("factor_id")
    library_index = json.loads(input_paths["library_index"].read_text(encoding="utf-8"))
    frozen = {item["factor_id"]: item for item in freeze["frozen_candidates"]}
    expected = set(frozen)
    if not all(set(frame.index) == expected for frame in (base, csi, liquid, params, library)):
        raise RuntimeError("Formal metric inputs do not cover the same frozen set")
    if set(economics) != expected or economics_payload.get("validation_metrics_visible") is not False:
        raise RuntimeError("Economic review is not an exact blinded review of the frozen set")
    if freeze.get("campaign_hash") != campaign.get("campaign_hash"):
        raise RuntimeError("Campaign and formula-freeze hashes differ")

    config = load_config()
    rows: list[dict[str, Any]] = []
    score_details: dict[str, Any] = {}
    decisions: dict[str, Any] = {}
    for factor_id, row in base.iterrows():
        metrics = row.to_dict()
        metrics.update(
            {
                "csi500_rank_ic": float(csi.loc[factor_id, "transfer_validation_rank_ic"]),
                "liquid_all_a_rank_ic": float(
                    liquid.loc[factor_id, "transfer_validation_rank_ic"]
                ),
                "parameter_stability": float(params.loc[factor_id, "parameter_stability"]),
                "max_abs_library_correlation": float(
                    library.loc[factor_id, "max_abs_library_correlation"]
                ),
            }
        )
        score = score_record(metrics, config)
        score_details[factor_id] = score
        quality = score["formal_quality_score"]
        failures = hard_gate_failures(pd.Series(metrics), config)
        if metrics["csi500_rank_ic"] < 0:
            failures.append("csi500_transfer")
        if metrics["liquid_all_a_rank_ic"] < 0:
            failures.append("liquid_all_a_transfer")
        if metrics["parameter_stability"] < 0.50:
            failures.append("parameter_stability")
        economic = economics[factor_id]
        if economic["economic_gate"] == "FAIL":
            failures.append("economic_gate")
        if quality is None:
            failures.append("incomplete_quality_score")
        failures = list(dict.fromkeys(failures))

        active_pairs = pairs.loc[
            pairs["factor_id"].eq(factor_id)
            & pairs["library_role"].eq("active_research")
        ].sort_values("average_abs_daily_spearman", ascending=False)
        active_above_gate = active_pairs.loc[
            active_pairs["average_abs_daily_spearman"].ge(
                config["hard_gates"]["dedup_correlation"]
            )
        ]
        replacement: dict[str, Any] | None = None
        independent = active_above_gate.empty
        if not independent:
            best = active_above_gate.iloc[0]
            match_id = str(best["library_factor_id"])
            replacement = {
                "candidate": factor_id,
                "best_active_match": match_id,
                "correlation": float(best["average_abs_daily_spearman"]),
                "active_matches_at_or_above_0_50": int(len(active_above_gate)),
                "quality_score_comparison_is_provisional_for_prior": True,
            }
            if match_id in prior.index and quality is not None:
                old = prior.loc[match_id]
                score_improvement = float(quality - old["provisional_composite_score"])
                validation_improvement = float(
                    metrics["validation_rank_ic"] / old["validation_rank_ic"] - 1
                )
                cost_not_worse = bool(
                    metrics["net_sharpe_10bps"] >= old["net_sharpe_10bps"]
                    and metrics["net_20bps_annualized_sharpe"]
                    >= old["net_sharpe_20bps"] - 0.25
                )
                replacement.update(
                    {
                        "prior_quality_score": float(old["provisional_composite_score"]),
                        "quality_score_improvement": score_improvement,
                        "prior_validation_rank_ic": float(old["validation_rank_ic"]),
                        "validation_ic_improvement": validation_improvement,
                        "cost_stress_not_materially_worse": cost_not_worse,
                        "passes_replacement_rules": bool(
                            score_improvement
                            >= config["hard_gates"]["min_replacement_score_improvement"]
                            and validation_improvement
                            >= config["hard_gates"]["min_replacement_ic_improvement"]
                            and len(active_above_gate) == 1
                            and metrics["parameter_stability"] >= 0.50
                            and cost_not_worse
                        ),
                    }
                )
            else:
                replacement["passes_replacement_rules"] = False

        passes_core = not failures and quality is not None and quality >= config["score_bands"]["qualified"]
        if passes_core and independent:
            decision = "admit"
            reason = "All formal gates pass and active-library correlation is below 0.50."
        elif passes_core and replacement and replacement.get("passes_replacement_rules"):
            decision = "replace"
            reason = (
                f"All formal gates pass; replaces provisional {replacement['best_active_match']} "
                "under score, validation-IC, uniqueness, parameter, and cost-stress rules."
            )
        elif (
            quality is not None
            and quality >= config["score_bands"]["research"]
            and economic["economic_gate"] != "FAIL"
            and metrics["validation_rank_ic"] > 0
        ):
            decision = "research"
            reason = "Economically usable but at least one formal core gate remains unmet."
        else:
            decision = "fail"
            reason = "Fails required statistical, robustness, economic, or completeness gates."
        tradable = bool(
            decision in {"admit", "replace"}
            and metrics["net_sharpe_10bps"] > 0
            and metrics["net_20bps_annualized_sharpe"] >= 0
        )
        decisions[factor_id] = {
            "decision": decision,
            "reason": reason,
            "hard_gate_failures": failures,
            "independent_of_active_research_library": independent,
            "replacement_audit": replacement,
            "tradable_core": tradable,
        }
        rows.append(
            {
                "factor_id": factor_id,
                "factor_name": row["factor_name"],
                "economic_family": row["economic_family"],
                "economic_gate": economic["economic_gate"],
                "direction_consistency": economic["direction_consistency"],
                "discovery_rank_ic": metrics["discovery_rank_ic"],
                "validation_rank_ic": metrics["validation_rank_ic"],
                "newey_west_t": metrics["newey_west_t"],
                "global_fdr_q": metrics["fdr_q"],
                "net_sharpe_10bps": metrics["net_sharpe_10bps"],
                "net_sharpe_20bps": metrics["net_20bps_annualized_sharpe"],
                "average_daily_turnover": metrics["average_daily_turnover"],
                "csi500_rank_ic": metrics["csi500_rank_ic"],
                "liquid_all_a_rank_ic": metrics["liquid_all_a_rank_ic"],
                "parameter_stability": metrics["parameter_stability"],
                "max_abs_library_correlation": metrics["max_abs_library_correlation"],
                "max_abs_active_research_correlation": library.loc[
                    factor_id, "max_abs_active_research_correlation"
                ],
                "best_library_match": library.loc[factor_id, "best_library_match"],
                "formal_quality_score": quality,
                "score_completeness": score["score_completeness"],
                "score_band": score_band(quality, config) if quality is not None else None,
                "hard_gate_failures": ",".join(failures),
                "decision": decision,
                "decision_reason": reason,
                "tradable_core": tradable,
            }
        )

    summary = pd.DataFrame(rows).sort_values(
        ["decision", "formal_quality_score", "validation_rank_ic"],
        ascending=[True, False, False],
        na_position="last",
    )
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    summary.to_csv(output_dir / "complete_factor_summary.csv", index=False)
    write_json_exclusive(output_dir / "score_components.json", score_details)
    write_json_exclusive(output_dir / "decision_audit.json", decisions)

    def library_payload(kind: str, selected: pd.DataFrame) -> dict[str, Any]:
        records = []
        for _, item in selected.iterrows():
            record = frozen[item["factor_id"]]
            records.append(
                {
                    **record,
                    "formal_quality_score": json_value(item["formal_quality_score"]),
                    "validation_rank_ic": json_value(item["validation_rank_ic"]),
                    "csi500_rank_ic": json_value(item["csi500_rank_ic"]),
                    "liquid_all_a_rank_ic": json_value(item["liquid_all_a_rank_ic"]),
                    "net_sharpe_10bps": json_value(item["net_sharpe_10bps"]),
                    "net_sharpe_20bps": json_value(item["net_sharpe_20bps"]),
                    "economic_gate": item["economic_gate"],
                    "decision": item["decision"],
                    "replaces": (
                        decisions[item["factor_id"]]["replacement_audit"]["best_active_match"]
                        if item["decision"] == "replace"
                        else None
                    ),
                }
            )
        return {
            "schema_version": "local_factor_library_v2",
            "campaign_version": campaign["campaign_version"],
            "campaign_hash": campaign["campaign_hash"],
            "formula_set_hash": freeze["formula_set_hash"],
            "library_kind": kind,
            "status": "formal",
            "factor_count": len(records),
            "factors": records,
        }

    libraries_dir = output_dir / "libraries"
    research = summary.loc[summary["decision"].isin({"admit", "replace", "research"})]
    predictive = summary.loc[summary["decision"].isin({"admit", "replace"})]
    tradable = summary.loc[summary["tradable_core"]]
    write_json_exclusive(
        libraries_dir / "research_library.json", library_payload("research_library", research)
    )
    write_json_exclusive(
        libraries_dir / "predictive_core.json", library_payload("predictive_core", predictive)
    )
    write_json_exclusive(
        libraries_dir / "tradable_core.json", library_payload("tradable_core", tradable)
    )
    benchmark_paths = {
        key: library_index["libraries"][key]
        for key in ("legacy_benchmark",)
    }
    write_json_exclusive(
        libraries_dir / "benchmark_control_library.json",
        {
            "library_kind": "benchmark_control_library",
            "status": "separate_from_local_admission",
            "source_library_index": str(input_paths["library_index"]),
            "source_library_index_sha256": sha256_file(input_paths["library_index"]),
            "benchmarks": benchmark_paths,
            "alpha158": {"status": "pending_local_construction"},
            "calibration_controls": {
                "status": "frozen_separate_library",
                "path": "skills/a-share-factor-miner/references/calibration_controls_v1.json",
            },
        },
    )

    trajectory_lines = []
    for _, item in summary.iterrows():
        factor_id = item["factor_id"]
        trajectory_lines.append(
            json.dumps(
                {
                    **frozen[factor_id],
                    "stage": "factor_validation_complete_metrics",
                    "status": item["decision"],
                    "hard_gate_failures": decisions[factor_id]["hard_gate_failures"],
                    "economic_review": economics[factor_id],
                    "metrics": {
                        key: json_value(value)
                        for key, value in item.to_dict().items()
                        if key not in {"factor_id", "factor_name"}
                    },
                    "score": score_details[factor_id],
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
    (output_dir / "validation_trajectory.jsonl").write_text(
        "\n".join(trajectory_lines) + "\n", encoding="utf-8"
    )

    report = [
        "# Local Ralph v4 complete campaign review",
        "",
        f"- Proposals: {campaign['budgets']['candidate_budget']}",
        f"- Globally frozen and validated: {len(summary)}",
        f"- Formal predictive core: {len(predictive)}",
        f"- Formal tradable core: {len(tradable)}",
        f"- Formula set hash: `{freeze['formula_set_hash']}`",
        "- Discovery: 2016-2020; factor validation: 2021-2022",
        "- Synthesis validation and lockbox remain unopened",
        "",
        "| Factor | Decision | Score | HS300 IC | CSI500 IC | Liquid A IC | Param | Net10 | Corr | Econ |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for _, item in summary.iterrows():
        score_text = (
            "NA" if pd.isna(item["formal_quality_score"]) else f"{item['formal_quality_score']:.2f}"
        )
        report.append(
            f"| {item['factor_id']} | {item['decision']} | {score_text} | "
            f"{item['validation_rank_ic']:.4f} | {item['csi500_rank_ic']:.4f} | "
            f"{item['liquid_all_a_rank_ic']:.4f} | {item['parameter_stability']:.2f} | "
            f"{item['net_sharpe_10bps']:.2f} | {item['max_abs_library_correlation']:.3f} | "
            f"{item['economic_gate']} |"
        )
    (output_dir / "campaign_review.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    run_manifest = {
        "created_at": pd.Timestamp.now(tz="Asia/Shanghai").isoformat(),
        "campaign_version": campaign["campaign_version"],
        "campaign_hash": campaign["campaign_hash"],
        "formula_set_hash": freeze["formula_set_hash"],
        "status": "campaign_review_complete",
        "validation_labels_opened": True,
        "generation_may_resume": False,
        "synthesis_validation_opened": False,
        "lockbox_opened": False,
        "validated_count": len(summary),
        "formal_predictive_count": len(predictive),
        "formal_tradable_count": len(tradable),
        "formal_research_count": len(research),
        "input_bindings": {
            name: {"path": str(path), "sha256": sha256_file(path)}
            for name, path in input_paths.items()
        },
    }
    write_json_exclusive(output_dir / "run_manifest.json", run_manifest)
    print(json.dumps(run_manifest, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
