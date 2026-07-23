#!/usr/bin/env python3
"""Seal a 40-proposal factor pack and its preregistered parameter plan."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json_exclusive(payload: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def load_records(path: Path, label: str) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        keys = ["proposals"] if label == "proposal" else ["parameters", "parameter_plans"]
        records = next((payload[key] for key in keys if key in payload), None)
    else:
        records = payload
    if not isinstance(records, list):
        raise ValueError(f"{label} file must be a list or contain a list payload")
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-manifest", required=True)
    parser.add_argument("--pack-number", type=int, required=True)
    parser.add_argument("--proposals", required=True)
    parser.add_argument("--parameter-plan", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    campaign_path = Path(args.campaign_manifest).resolve()
    proposals_path = Path(args.proposals).resolve()
    parameter_path = Path(args.parameter_plan).resolve()
    output_path = Path(args.output).resolve()
    for path in (campaign_path, proposals_path, parameter_path):
        if not path.exists():
            raise FileNotFoundError(path)

    campaign = json.loads(campaign_path.read_text(encoding="utf-8"))
    maximum_packs = int(campaign["budgets"]["maximum_packs"])
    if not 1 <= args.pack_number <= maximum_packs:
        raise ValueError(f"pack-number must be between 1 and {maximum_packs}")

    proposals = load_records(proposals_path, "proposal")
    required = {
        "candidate_id",
        "factor_name",
        "formula",
        "economic_hypothesis",
        "economic_family",
        "data_domain",
        "target_patterns",
        "internal_sub_batch",
    }
    if len(proposals) != 40:
        raise ValueError(f"Pack-40 requires exactly 40 proposals, found {len(proposals)}")
    for position, record in enumerate(proposals, start=1):
        missing = required - set(record)
        if missing:
            raise ValueError(f"proposal {position} missing fields: {sorted(missing)}")
    candidate_ids = [str(record["candidate_id"]) for record in proposals]
    formulas = [str(record["formula"]) for record in proposals]
    if len(set(candidate_ids)) != 40:
        raise ValueError("candidate_id values must be unique")
    if len(set(formulas)) != 40:
        raise ValueError("formula strings must be unique within a pack")
    sub_batches = [int(record["internal_sub_batch"]) for record in proposals]
    counts = {number: sub_batches.count(number) for number in range(1, 5)}
    if counts != {1: 10, 2: 10, 3: 10, 4: 10}:
        raise ValueError(f"expected four sub-batches of ten, found {counts}")

    parameters = load_records(parameter_path, "parameter")
    parameter_by_id = {str(record.get("candidate_id")): record for record in parameters}
    if set(parameter_by_id) != set(candidate_ids) or len(parameters) != 40:
        raise ValueError("parameter plan must cover each of the 40 candidate IDs exactly once")
    for candidate_id, record in parameter_by_id.items():
        parameter_free = record.get("parameter_free") is True
        variants = record.get("formula_variants")
        has_variants = isinstance(variants, list) and len(variants) > 0
        if parameter_free == has_variants:
            raise ValueError(
                f"{candidate_id}: declare exactly one of parameter_free=true or formula_variants"
            )

    formula_hashes = {
        candidate_id: hashlib.sha256(formula.encode("utf-8")).hexdigest()
        for candidate_id, formula in zip(candidate_ids, formulas, strict=True)
    }
    pack_preparer_path = PROJECT_ROOT / "skills" / "a-share-factor-miner" / "scripts" / "prepare_factor_pack.py"
    pack_finalizer_path = PROJECT_ROOT / "skills" / "a-share-factor-miner" / "scripts" / "finalize_factor_pack.py"
    discovery_evaluator_path = PROJECT_ROOT / "local_research" / "formal_pipeline" / "screen_discovery.py"
    for path in (pack_preparer_path, pack_finalizer_path, discovery_evaluator_path):
        if not path.exists():
            raise FileNotFoundError(path)
    payload = {
        "campaign_version": campaign["campaign_version"],
        "campaign_hash": campaign["campaign_hash"],
        "pack_number": args.pack_number,
        "pack_size": 40,
        "status": "sealed_before_discovery",
        "sealed_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
        "proposals_path": str(proposals_path),
        "proposals_sha256": sha256_file(proposals_path),
        "parameter_plan_path": str(parameter_path),
        "parameter_plan_sha256": sha256_file(parameter_path),
        "candidate_formula_hashes": formula_hashes,
        "pack_preparer_path": str(pack_preparer_path),
        "pack_preparer_sha256": sha256_file(pack_preparer_path),
        "pack_finalizer_path": str(pack_finalizer_path),
        "pack_finalizer_sha256": sha256_file(pack_finalizer_path),
        "discovery_evaluator_path": str(discovery_evaluator_path),
        "discovery_evaluator_sha256": sha256_file(discovery_evaluator_path),
        "sub_batch_counts": counts,
        "required_outputs": [
            "lint_results.csv",
            "discovery_metrics.csv",
            "pack_summary.md",
            "trajectory_append.jsonl",
            "pattern_state_after_pack.json",
        ],
        "visibility": "discovery_only",
        "pattern_state_update": "once_after_all_40_outcomes",
    }
    write_json_exclusive(payload, output_path)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
