#!/usr/bin/env python3
"""Evaluate one frozen campaign formula set on the sealed factor-validation period."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

from evaluate_factors import (
    PROJECT_ROOT,
    FormulaExecutor,
    bh_qvalues,
    evaluate_record,
    exact_daily_duplicate_map,
    hard_gate_failures,
    load_config,
    load_factor_records,
    load_panel,
    score_band,
    score_record,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_parameter_plan(path: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("parameter_plans", [])
    by_id = {str(record.get("candidate_id")): record for record in records}
    if len(records) != len(by_id):
        raise RuntimeError("Pre-registered parameter plan contains duplicate candidate IDs")
    return payload, by_id


def load_compatible_history(
    paths: list[Path], panel_manifest: dict[str, Any], evaluator_version: str
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in paths:
        run_path = path.parent / "run_manifest.json"
        if not run_path.exists():
            raise FileNotFoundError(f"Missing history run manifest: {run_path}")
        run = json.loads(run_path.read_text(encoding="utf-8"))
        expected = {
            "evaluator_version": evaluator_version,
            "panel_sha256": panel_manifest["output_sha256"],
            "data_snapshot": panel_manifest["data_snapshot"],
            "universe_version": panel_manifest["universe_sha256"],
            "label_version": panel_manifest["label_version"],
        }
        mismatches = {
            key: (run.get(key), value)
            for key, value in expected.items()
            if run.get(key) != value
        }
        if mismatches:
            raise RuntimeError(f"Incompatible FDR history {path}: {mismatches}")
        frame = pd.read_csv(path, usecols=["factor_id", "formula_hash", "one_sided_p"])
        frame["history_source"] = str(path.resolve())
        frames.append(frame)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def global_qvalues(history: pd.DataFrame, current: pd.DataFrame) -> tuple[pd.Series, int]:
    columns = ["factor_id", "formula_hash", "one_sided_p"]
    combined = pd.concat([history, current[columns]], ignore_index=True)
    combined["one_sided_p"] = pd.to_numeric(combined["one_sided_p"], errors="coerce")
    combined = combined.loc[
        combined["formula_hash"].notna()
        & combined["one_sided_p"].map(lambda value: math.isfinite(value) and 0 <= value <= 1)
    ].copy()
    disagreements = combined.groupby("formula_hash")["one_sided_p"].agg(["min", "max"])
    if ((disagreements["max"] - disagreements["min"]) > 1e-10).any():
        bad = disagreements.loc[(disagreements["max"] - disagreements["min"]) > 1e-10]
        raise RuntimeError(f"Same formula hash has incompatible p-values:\n{bad}")
    unique = combined.drop_duplicates("formula_hash", keep="first").copy()
    unique["global_fdr_q"] = bh_qvalues(unique["one_sided_p"])
    mapping = unique.set_index("formula_hash")["global_fdr_q"]
    return current["formula_hash"].map(mapping), len(unique)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", required=True)
    parser.add_argument("--freeze-manifest", required=True)
    parser.add_argument("--campaign-manifest", required=True)
    parser.add_argument("--script-version", required=True)
    parser.add_argument("--fdr-history-summary", action="append", default=[])
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    panel_path = Path(args.panel).resolve()
    panel_manifest_path = panel_path.with_suffix(".manifest.json")
    panel_manifest = json.loads(panel_manifest_path.read_text(encoding="utf-8"))
    freeze_path = Path(args.freeze_manifest).resolve()
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    campaign_path = Path(args.campaign_manifest).resolve()
    campaign = json.loads(campaign_path.read_text(encoding="utf-8"))
    if freeze.get("status") != "formula_frozen_validation_sealed":
        raise RuntimeError("Formula set is not frozen with validation sealed")
    if freeze.get("validation_labels_opened") is not False:
        raise RuntimeError("Freeze manifest says validation was already opened")
    if campaign.get("campaign_hash") != freeze.get("campaign_hash"):
        raise RuntimeError("Campaign and formula-freeze hashes differ")
    if campaign.get("status") != "discovery_open_validation_sealed":
        raise RuntimeError("Campaign is not in the expected pre-validation state")
    if panel_manifest.get("research_stage") != "factor_validation":
        raise RuntimeError("Validator requires a factor_validation panel")
    if panel_manifest.get("output_sha256") != sha256_file(panel_path):
        raise RuntimeError("Factor-validation panel hash differs from its manifest")
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
        raise RuntimeError(f"Factor-validation panel identity mismatch: {mismatches}")
    if freeze.get("data_snapshot") != campaign["data_snapshot"]:
        raise RuntimeError("Formula freeze and campaign data snapshots differ")
    selection_policy_path = freeze_path.parent / "selection_policy.json"
    if (
        not selection_policy_path.exists()
        or sha256_file(selection_policy_path) != freeze.get("selection_policy_sha256")
    ):
        raise RuntimeError("Global discovery selection policy is missing or changed")
    if canonical_json_hash(freeze.get("frozen_candidates", [])) != freeze.get(
        "formula_set_hash"
    ):
        raise RuntimeError("Frozen formula-set hash is invalid")
    parameter_plan_value = freeze.get("parameter_plan")
    parameter_plan_hash = freeze.get("parameter_plan_sha256")
    if not parameter_plan_value or not parameter_plan_hash:
        raise RuntimeError("Frozen set has no pre-registered parameter plan; validation is blocked")
    parameter_plan_path = Path(parameter_plan_value).resolve()
    if not parameter_plan_path.exists() or sha256_file(parameter_plan_path) != parameter_plan_hash:
        raise RuntimeError("Pre-registered parameter plan is missing or changed")
    parameter_payload, parameter_by_id = load_parameter_plan(parameter_plan_path)
    if parameter_payload.get("status") != "consolidated_from_sealed_pack_plans":
        raise RuntimeError("Parameter plan is not a sealed-pack consolidation")
    if parameter_payload.get("campaign_hash") != campaign["campaign_hash"]:
        raise RuntimeError("Parameter plan and campaign hashes differ")
    if parameter_payload.get("validation_labels_opened") is not False:
        raise RuntimeError("Parameter plan reports opened validation labels")

    config = load_config()
    if config["version"] != campaign["evaluator_version"]:
        raise RuntimeError("Active evaluator version differs from the frozen campaign")
    script_dir = (PROJECT_ROOT / "factor_script" / args.script_version).resolve()
    records_by_id = {
        record["factor_id"]: record
        for record in load_factor_records(script_dir)
    }
    frozen_by_id = {item["factor_id"]: item for item in freeze["frozen_candidates"]}
    ordered_ids = [item["factor_id"] for item in freeze["frozen_candidates"]]
    if len(ordered_ids) != freeze["frozen_candidate_count"] or len(set(ordered_ids)) != len(ordered_ids):
        raise RuntimeError("Frozen candidate count or uniqueness mismatch")
    if not set(ordered_ids).issubset(parameter_by_id):
        raise RuntimeError("Pre-registered parameter plan does not cover every frozen factor")
    if len(parameter_by_id) != int(campaign["budgets"]["candidate_budget"]):
        raise RuntimeError("Pre-registered parameter plan does not cover the full campaign")
    for factor_id in ordered_ids:
        if factor_id not in records_by_id:
            raise RuntimeError(f"Missing frozen factor script: {factor_id}")
        record = records_by_id[factor_id]
        frozen = frozen_by_id[factor_id]
        if record["formula_hash"] != frozen["formula_hash"] or record["formula"] != frozen["formula"]:
            raise RuntimeError(f"Frozen formula changed: {factor_id}")

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=False)

    # This is the single intentional opening of 2021-2022 for the frozen set.
    metadata = load_panel(panel_path)
    executor = FormulaExecutor(str(panel_path), start_date=20150101, end_date=20221231)
    results: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    daily_outputs: dict[str, pd.DataFrame] = {}
    for position, factor_id in enumerate(ordered_ids, start=1):
        record = records_by_id[factor_id]
        try:
            result, daily = evaluate_record(record, executor, metadata)
            if int(result["train_direction"]) != int(frozen_by_id[factor_id]["train_direction"]):
                raise RuntimeError("Discovery direction differs from frozen direction")
            score = score_record(result, config)
            results.append(
                {
                    **result,
                    **{
                        key: value
                        for key, value in score.items()
                        if key not in {"metric_points", "section_points", "section_available_weight"}
                    },
                    "score_components_json": json.dumps(score["metric_points"], sort_keys=True),
                    "economic_family": frozen_by_id[factor_id]["economic_family"],
                    "frozen_discovery_tier": frozen_by_id[factor_id]["discovery_tier"],
                }
            )
            daily_outputs[factor_id] = daily
            print(
                f"[{position}/{len(ordered_ids)}] {factor_id}: "
                f"discovery={result['discovery_rank_ic']:.4f} "
                f"validation={result['validation_rank_ic']:.4f}",
                flush=True,
            )
        except Exception as exc:
            failures.append({**record, "error": str(exc)})
            print(f"[{position}/{len(ordered_ids)}] {factor_id}: FAILED {exc}", flush=True)

    summary = pd.DataFrame(results)
    if len(summary) != len(ordered_ids) or failures:
        raise RuntimeError(f"Frozen validation incomplete: completed={len(summary)} failures={failures}")

    history_paths = [Path(path).resolve() for path in args.fdr_history_summary]
    history = load_compatible_history(history_paths, panel_manifest, config["version"])
    summary["fdr_q"], global_test_count = global_qvalues(history, summary)
    daily_signatures, duplicate_of = exact_daily_duplicate_map(daily_outputs)
    summary["exact_daily_signature"] = summary["factor_id"].map(daily_signatures)
    summary["duplicate_of"] = summary["factor_id"].map(duplicate_of)
    summary["hard_gate_failures"] = [
        ",".join(hard_gate_failures(row, config)) for _, row in summary.iterrows()
    ]
    is_duplicate = summary["duplicate_of"].notna()
    summary.loc[is_duplicate, "hard_gate_failures"] = summary.loc[
        is_duplicate, "hard_gate_failures"
    ].map(lambda value: ",".join(filter(None, [value, "exact_daily_duplicate"])))
    summary["passes_available_hard_gates"] = summary["hard_gate_failures"].eq("")
    summary["provisional_band"] = summary["normalized_observed_score"].map(
        lambda value: score_band(value, config)
    )
    summary["admission_status"] = "pending_transfer_parameter_economic_review"
    summary = summary.sort_values(
        ["passes_available_hard_gates", "validation_rank_ic"], ascending=[False, False]
    )
    summary.to_csv(output_dir / "factor_summary.csv", index=False)
    for factor_id, daily in daily_outputs.items():
        daily.to_parquet(output_dir / f"factor_{factor_id}_daily_metrics.parquet")
    (output_dir / "failures.json").write_text("[]\n", encoding="utf-8")
    run_manifest = {
        "created_at": pd.Timestamp.now(tz="Asia/Shanghai").isoformat(),
        "campaign_version": freeze["campaign_version"],
        "campaign_hash": freeze["campaign_hash"],
        "formula_set_hash": freeze["formula_set_hash"],
        "parameter_plan": str(parameter_plan_path),
        "parameter_plan_sha256": parameter_plan_hash,
        "campaign_manifest": str(campaign_path),
        "campaign_manifest_sha256": sha256_file(campaign_path),
        "freeze_manifest": str(freeze_path),
        "freeze_manifest_sha256": sha256_file(freeze_path),
        "selection_policy_sha256": freeze["selection_policy_sha256"],
        "script_version": args.script_version,
        "validator_path": str(Path(__file__).resolve()),
        "validator_sha256": sha256_file(Path(__file__).resolve()),
        "evaluator_version": config["version"],
        "status": "frozen_factor_validation_complete_no_admission",
        "validation_labels_opened": True,
        "generation_may_resume": False,
        "panel": str(panel_path),
        "panel_sha256": panel_manifest["output_sha256"],
        "data_snapshot": panel_manifest["data_snapshot"],
        "universe_version": panel_manifest["universe_sha256"],
        "label_version": panel_manifest["label_version"],
        "factor_count": len(ordered_ids),
        "completed": len(summary),
        "failed": 0,
        "global_fdr_test_count": global_test_count,
        "fdr_history_sources": [str(path) for path in history_paths],
        "discovery": ["2016-01-01", "2020-12-31"],
        "factor_validation": ["2021-01-01", "2022-12-31"],
        "warning": "Scores remain provisional until transfer, parameter, library-correlation, and economic review are complete.",
    }
    (output_dir / "run_manifest.json").write_text(
        json.dumps(run_manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"Validated frozen set; global FDR history contains {global_test_count} unique formulas",
        flush=True,
    )


if __name__ == "__main__":
    main()
