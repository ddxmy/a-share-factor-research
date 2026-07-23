#!/usr/bin/env python3
"""Build clean versioned factor-library registries without deleting research history."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def write_json_exclusive(payload: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def formula_hash(formula: str) -> str:
    return hashlib.sha256(formula.encode("utf-8")).hexdigest()


def scan_scripts(root: Path) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for path in sorted((root / "factor_script").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        constants: dict[str, str] = {}
        for node in tree.body:
            if not (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id in {"FACTOR_NAME", "FORMULA"}
            ):
                continue
            try:
                constants[node.targets[0].id] = str(ast.literal_eval(node.value))
            except (ValueError, TypeError):
                continue
        if {"FACTOR_NAME", "FORMULA"}.issubset(constants):
            records.append(
                {
                    "factor_id": path.stem,
                    "factor_name": constants["FACTOR_NAME"],
                    "formula": constants["FORMULA"],
                    "formula_hash": formula_hash(constants["FORMULA"]),
                    "script_path": str(path.relative_to(root)),
                }
            )
    return records


def normalize_local(source: dict, kind: str, source_path: Path, root: Path) -> dict:
    factors = source.get("factors", [])
    return {
        "schema_version": "factor_library_registry_v1",
        "library_kind": kind,
        "status": source.get("status", "unknown"),
        "formal_admission_count": 0,
        "factor_count": len(factors),
        "source_artifact": str(source_path.relative_to(root)),
        "blocking_audits": source.get("blocking_audits", []),
        "factors": factors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--output-dir")
    parser.add_argument("--as-of", default="2026-07-22")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    source_dir = Path(args.source_dir).resolve()
    output_dir = (
        Path(args.output_dir).resolve()
        if args.output_dir
        else root / "data" / "libraries"
    )
    source_paths = {
        "research": source_dir / "research_library.json",
        "predictive": source_dir / "predictive_core_candidates.json",
        "tradable": source_dir / "tradable_core_candidates.json",
    }
    legacy_path = root / "data" / "factor_library.json"
    for path in [*source_paths.values(), legacy_path]:
        if not path.exists():
            raise FileNotFoundError(path)
    output_dir.mkdir(parents=True, exist_ok=True)

    sources = {name: load_json(path) for name, path in source_paths.items()}
    outputs = {
        "local_research_provisional.json": normalize_local(
            sources["research"], "local_research", source_paths["research"], root
        ),
        "local_predictive_provisional.json": normalize_local(
            sources["predictive"], "local_predictive_core", source_paths["predictive"], root
        ),
        "local_tradable_provisional.json": normalize_local(
            sources["tradable"], "local_tradable_core", source_paths["tradable"], root
        ),
    }

    scripts = scan_scripts(root)
    script_by_formula = {record["formula"]: record for record in scripts}
    legacy_factors: list[dict] = []
    for factor in load_json(legacy_path):
        script = script_by_formula.get(factor["formula"], {})
        legacy_factors.append(
            {
                **factor,
                "factor_id": script.get("factor_id", factor["factor_id"]),
                "legacy_numeric_id": factor["factor_id"],
                "formula_hash": formula_hash(factor["formula"]),
                "script_path": script.get("script_path"),
                "library_role": "benchmark_only",
                "status": "legacy_score_not_comparable_to_local_score",
            }
        )
    outputs["benchmark_legacy_factorminer.json"] = {
        "schema_version": "factor_library_registry_v1",
        "library_kind": "benchmark_control",
        "status": "frozen_legacy_benchmark",
        "formal_admission_count": 0,
        "factor_count": len(legacy_factors),
        "source_artifact": str(legacy_path.relative_to(root)),
        "factors": legacy_factors,
    }

    retained_ids = {
        str(factor["factor_id"])
        for source in outputs.values()
        for factor in source.get("factors", [])
    }
    trajectory_only = [
        {
            "factor_id": record["factor_id"],
            "formula_hash": record["formula_hash"],
            "script_path": record["script_path"],
            "status": "trajectory_only_not_active_under_current_protocol",
        }
        for record in scripts
        if record["factor_id"] not in retained_ids
    ]
    outputs["trajectory_only_registry.json"] = {
        "schema_version": "factor_library_registry_v1",
        "library_kind": "trajectory_only",
        "status": "excluded_from_all_default_factor_selection",
        "factor_count": len(trajectory_only),
        "files_deleted": 0,
        "factors": trajectory_only,
    }

    for filename, payload in outputs.items():
        write_json_exclusive(payload, output_dir / filename)

    predictive_count = outputs["local_predictive_provisional.json"]["factor_count"]
    research_count = outputs["local_research_provisional.json"]["factor_count"]
    tradable_count = outputs["local_tradable_provisional.json"]["factor_count"]
    index = {
        "schema_version": "factor_library_index_v1",
        "generated_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
        "as_of": args.as_of,
        "policy": {
            "canonical_entry_point": True,
            "script_presence_implies_membership": False,
            "history_physically_deleted": False,
            "default_evaluation_library": "local_research_provisional.json",
        },
        "libraries": {
            "local_research": {
                "path": "data/libraries/local_research_provisional.json",
                "status": "provisional",
                "factor_count": research_count,
            },
            "local_predictive_core": {
                "path": "data/libraries/local_predictive_provisional.json",
                "status": "provisional_no_formal_admission",
                "factor_count": predictive_count,
                "formal_admission_count": 0,
            },
            "local_tradable_core": {
                "path": "data/libraries/local_tradable_provisional.json",
                "status": "provisional_no_formal_admission",
                "factor_count": tradable_count,
                "formal_admission_count": 0,
            },
            "legacy_benchmark": {
                "path": "data/libraries/benchmark_legacy_factorminer.json",
                "status": "benchmark_only",
                "factor_count": len(legacy_factors),
            },
            "trajectory_only": {
                "path": "data/libraries/trajectory_only_registry.json",
                "status": "excluded_from_defaults",
                "factor_count": len(trajectory_only),
            },
        },
        "comparison_readiness": {
            "ready_for_formal_alpha158_comparison": False,
            "formal_predictive_count": 0,
            "provisional_predictive_count": predictive_count,
            "minimum_formal_predictive_count": 8,
            "minimum_economic_families": 4,
            "preferred_formal_predictive_count": [12, 20],
            "preferred_tradable_count": [3, 5],
            "shortfall_to_minimum": 8,
            "provisional_shortfall_to_minimum_if_requalified": max(0, 8 - predictive_count),
        },
    }
    write_json_exclusive(index, output_dir / "library_index.json")
    print(json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
