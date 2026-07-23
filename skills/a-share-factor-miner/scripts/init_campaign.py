#!/usr/bin/env python3
"""Create an immutable blinded factor-mining campaign manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo
from datetime import datetime


DEFAULT_FAMILIES = [
    "overnight_intraday_decomposition",
    "price_pressure_reversal",
    "trend_quality_path_efficiency",
    "price_volume_turnover_divergence",
    "liquidity_amount_shocks",
    "volatility_asymmetry",
    "return_tails_skewness",
    "signed_volume_accumulation",
    "range_location_anchoring",
    "conditional_regimes",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json_exclusive(payload: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(path, flags, 0o644)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--campaign-version", required=True)
    parser.add_argument("--data-snapshot", required=True)
    parser.add_argument("--universe-version", required=True)
    parser.add_argument("--label-version", required=True)
    parser.add_argument("--evaluator-version", required=True)
    parser.add_argument("--evaluator-freeze")
    parser.add_argument("--discovery-panel", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--candidate-budget", type=int, default=120)
    parser.add_argument("--pack-size", type=int, default=40)
    parser.add_argument("--sub-batch-size", type=int, default=10)
    parser.add_argument("--maximum-packs", type=int, default=3)
    parser.add_argument("--data-domain-registry")
    parser.add_argument("--library-index")
    parser.add_argument("--minimum-frozen", type=int, default=12)
    parser.add_argument("--target-frozen-low", type=int, default=15)
    parser.add_argument("--target-frozen-high", type=int, default=25)
    parser.add_argument("--family", action="append")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    panel = Path(args.discovery_panel).resolve()
    output = Path(args.output).resolve()
    operator_path = root / "scripts" / "operators" / "operator_library.py"
    pattern_path = root / "data" / "experience_memory.json"
    legacy_library_path = root / "data" / "factor_library.json"
    domain_path = (
        Path(args.data_domain_registry).resolve()
        if args.data_domain_registry
        else Path(__file__).resolve().parents[1] / "references" / "data_domains_v1.json"
    )
    library_index_path = (
        Path(args.library_index).resolve()
        if args.library_index
        else root / "data" / "libraries" / "library_index.json"
    )
    evaluator_freeze_path = (
        Path(args.evaluator_freeze).resolve()
        if args.evaluator_freeze
        else Path(__file__).resolve().parents[1] / "references" / "evaluator_freeze_v1.json"
    )
    for path in [
        operator_path,
        pattern_path,
        legacy_library_path,
        domain_path,
        library_index_path,
        evaluator_freeze_path,
        panel,
    ]:
        if not path.exists():
            raise FileNotFoundError(path)
    panel_manifest_path = panel.with_suffix(".manifest.json")
    if not panel_manifest_path.exists():
        raise FileNotFoundError(panel_manifest_path)
    panel_manifest = json.loads(panel_manifest_path.read_text(encoding="utf-8"))
    if panel_manifest.get("research_stage") != "discovery":
        raise ValueError("Campaign discovery panel must have research_stage=discovery")
    if panel_manifest.get("label_visibility") != "2016-01-01_to_2020-12-31_only":
        raise ValueError("Campaign discovery panel has an unexpected label-visibility policy")
    if panel_manifest.get("warmup_labels_masked") is not True:
        raise ValueError("Campaign discovery panel must mask warm-up labels")
    if panel_manifest.get("output_sha256") != sha256_file(panel):
        raise ValueError("Discovery panel hash does not match its manifest")
    if args.data_snapshot != panel_manifest.get("data_snapshot"):
        raise ValueError("--data-snapshot must match the discovery panel manifest")
    if args.label_version != panel_manifest.get("label_version"):
        raise ValueError("--label-version must match the discovery panel manifest")

    evaluator_freeze = json.loads(evaluator_freeze_path.read_text(encoding="utf-8"))
    if evaluator_freeze.get("status") != "frozen":
        raise ValueError("Evaluator freeze manifest is not frozen")
    if evaluator_freeze.get("evaluator_version") != args.evaluator_version:
        raise ValueError("--evaluator-version must match the evaluator freeze manifest")
    for artifact_name in (
        "score_config",
        "controls",
        "calibration_report",
        "calibration_scores",
        "invalid_control_audit",
    ):
        artifact = evaluator_freeze[artifact_name]
        artifact_path = root / artifact["path"]
        if not artifact_path.exists():
            raise FileNotFoundError(artifact_path)
        if sha256_file(artifact_path) != artifact["sha256"]:
            raise ValueError(f"Frozen evaluator artifact hash changed: {artifact_name}")
    for artifact_name, artifact in evaluator_freeze["implementation"].items():
        artifact_path = root / artifact["path"]
        if not artifact_path.exists():
            raise FileNotFoundError(artifact_path)
        if sha256_file(artifact_path) != artifact["sha256"]:
            raise ValueError(f"Frozen evaluator implementation hash changed: {artifact_name}")
    calibration_report = json.loads(
        (root / evaluator_freeze["calibration_report"]["path"]).read_text(encoding="utf-8")
    )
    if calibration_report.get("freeze_decision") is not True:
        raise ValueError("Evaluator calibration did not authorize a freeze")
    if calibration_report.get("config_sha256") != evaluator_freeze["score_config"]["sha256"]:
        raise ValueError("Calibration report is not bound to the frozen score config")
    if calibration_report.get("controls_sha256") != evaluator_freeze["controls"]["sha256"]:
        raise ValueError("Calibration report is not bound to the frozen controls")
    if evaluator_freeze["data_binding"]["snapshot"] != args.data_snapshot:
        raise ValueError("Campaign data snapshot differs from the evaluator freeze")
    if evaluator_freeze["data_binding"]["label_version"] != args.label_version:
        raise ValueError("Campaign label version differs from the evaluator freeze")
    if any(
        value <= 0
        for value in (
            args.candidate_budget,
            args.pack_size,
            args.sub_batch_size,
            args.maximum_packs,
        )
    ):
        raise ValueError("Campaign budgets must be positive")
    if args.pack_size != 40 or args.sub_batch_size != 10:
        raise ValueError("Pack-40 requires --pack-size 40 and --sub-batch-size 10")
    if args.candidate_budget > args.pack_size * args.maximum_packs:
        raise ValueError("candidate-budget exceeds pack-size * maximum-packs")
    if not (0 < args.minimum_frozen <= args.target_frozen_low <= args.target_frozen_high):
        raise ValueError("Invalid frozen-candidate targets")

    families = args.family or DEFAULT_FAMILIES
    if len(set(families)) < 8:
        raise ValueError("Campaign must pre-register at least eight economic families")
    identity = {
        "campaign_version": args.campaign_version,
        "candidate_budget": args.candidate_budget,
        "pack_size": args.pack_size,
        "maximum_packs": args.maximum_packs,
        "data_snapshot": args.data_snapshot,
        "data_snapshot_from_panel": panel_manifest["data_snapshot"],
        "discovery_dates": ["2016-01-01", "2020-12-31"],
        "factor_validation_dates": ["2021-01-01", "2022-12-31"],
        "synthesis_validation_dates": ["2023-01-01", "2024-12-31"],
        "lockbox_dates": ["2025-01-01", "latest_complete_day"],
        "universe_version": args.universe_version,
        "label_version": args.label_version,
        "evaluator_version": args.evaluator_version,
        "evaluator_freeze_hash": sha256_file(evaluator_freeze_path),
        "evaluator_score_config_hash": evaluator_freeze["score_config"]["sha256"],
        "evaluator_controls_hash": evaluator_freeze["controls"]["sha256"],
        "evaluator_calibration_report_hash": evaluator_freeze["calibration_report"]["sha256"],
        "operator_library_hash": sha256_file(operator_path),
        "pattern_state_hash": sha256_file(pattern_path),
        "legacy_library_hash": sha256_file(legacy_library_path),
        "active_library_index_hash": sha256_file(library_index_path),
        "data_domain_registry_version": json.loads(
            domain_path.read_text(encoding="utf-8")
        )["version"],
        "data_domain_registry_hash": sha256_file(domain_path),
        "economic_families": list(dict.fromkeys(families)),
    }
    campaign_hash = hashlib.sha256(
        json.dumps(identity, sort_keys=True).encode("utf-8")
    ).hexdigest()
    payload = {
        **identity,
        "campaign_hash": campaign_hash,
        "created_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
        "status": "discovery_open_validation_sealed",
        "budgets": {
            "candidate_budget": args.candidate_budget,
            "pack_size": args.pack_size,
            "internal_sub_batch_size": args.sub_batch_size,
            "maximum_packs": args.maximum_packs,
            "minimum_packs_before_yield_stop": 2,
            "marginal_yield_window_packs": 2,
            "minimum_new_independent_survivors_in_window": 1,
        },
        "freeze_targets": {
            "minimum_frozen_candidates": args.minimum_frozen,
            "target_frozen_candidates": [args.target_frozen_low, args.target_frozen_high],
            "target_predictive_core": [5, 8],
            "target_tradable_core": [3, 5],
            "maximum_per_family_or_cluster": 3,
        },
        "comparison_readiness": {
            "minimum_predictive_core": 8,
            "minimum_economic_families": 4,
            "preferred_predictive_core": [12, 20],
            "preferred_tradable_core": [3, 5],
        },
        "economic_families": list(dict.fromkeys(families)),
        "discovery_panel": str(panel),
        "discovery_panel_sha256": sha256_file(panel),
        "discovery_panel_manifest": str(panel_manifest_path),
        "visibility_policy": {
            "generator_may_read": [
                "skills/a-share-factor-miner",
                "scripts/operators/operator_library.py",
                "data/experience_memory.json",
                "data/libraries/library_index.json",
                "benchmark and trajectory formula catalogs without hidden labels",
                "campaign discovery artifacts",
            ],
            "generator_must_not_read": [
                "factor-validation results",
                "CSI500 or liquid-all-A transfer results",
                "2023-2024 synthesis-validation labels or results",
                "2025+ lockbox labels or results",
            ],
            "factor_validation_opens_only_after_formula_freeze": True,
            "generation_resumes_after_validation": False,
        },
        "library_artifacts": [
            "candidate_trajectory",
            "research_library",
            "predictive_core_library",
            "tradable_core_library",
            "benchmark_control_library",
        ],
        "pack_protocol": {
            "proposals_per_pack": 40,
            "internal_sub_batches": 4,
            "proposals_per_sub_batch": 10,
            "seal_parameter_plan_before_discovery": True,
            "load_discovery_panel_once_per_pack": True,
            "update_pattern_state_once_after_pack": True,
        },
        "deviations": [],
    }
    write_json_exclusive(payload, output)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
