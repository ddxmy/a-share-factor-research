#!/usr/bin/env python3
"""Finalize discovery-only Pack-40 artifacts and append its auditable trajectory."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ELIGIBLE_TIERS = {
    "discovery_research": 1,
    "discovery_qualified": 2,
    "discovery_implementation": 3,
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_safe(value: Any) -> Any:
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def write_text_exclusive(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(text)


def priority(row: pd.Series) -> tuple[Any, ...]:
    return (
        -ELIGIBLE_TIERS[str(row["discovery_tier"])],
        -float(row["discovery_rank_ic"]),
        -float(row["newey_west_t"]),
        -float(row["net_sharpe_10bps"]),
        str(row["factor_id"]),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-manifest", required=True)
    parser.add_argument("--pack-manifest", required=True)
    parser.add_argument("--lint-results", required=True)
    parser.add_argument("--discovery-dir", required=True)
    parser.add_argument("--experience-memory", required=True)
    parser.add_argument("--campaign-trajectory", required=True)
    parser.add_argument("--correlation-threshold", type=float, default=0.50)
    parser.add_argument("--family-cap", type=int, default=3)
    args = parser.parse_args()

    campaign_path = Path(args.campaign_manifest).resolve()
    pack_path = Path(args.pack_manifest).resolve()
    lint_path = Path(args.lint_results).resolve()
    discovery_dir = Path(args.discovery_dir).resolve()
    memory_path = Path(args.experience_memory).resolve()
    campaign_trajectory_path = Path(args.campaign_trajectory).resolve()
    campaign = json.loads(campaign_path.read_text(encoding="utf-8"))
    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    if pack.get("pack_finalizer_path") and (
        sha256_file(Path(pack["pack_finalizer_path"])) != pack["pack_finalizer_sha256"]
    ):
        raise RuntimeError("Pack finalizer changed after pack seal")
    run = json.loads((discovery_dir / "run_manifest.json").read_text(encoding="utf-8"))
    if pack["campaign_hash"] != campaign["campaign_hash"] or run["campaign_hash"] != campaign["campaign_hash"]:
        raise RuntimeError("Campaign, pack, and discovery run hashes differ")
    if run.get("validation_labels_opened") is not False or run.get("metadata_read_end") != "2020-12-31":
        raise RuntimeError("Discovery run visibility violation")
    if sha256_file(Path(pack["proposals_path"])) != pack["proposals_sha256"]:
        raise RuntimeError("Proposals changed after seal")
    if sha256_file(lint_path) != run["lint_results_sha256"]:
        raise RuntimeError("Lint results differ from the discovery run binding")

    proposals_payload = json.loads(Path(pack["proposals_path"]).read_text(encoding="utf-8"))
    proposals = proposals_payload.get("proposals", proposals_payload)
    proposal_by_id = {record["candidate_id"]: record for record in proposals}
    lint = pd.read_csv(lint_path).set_index("candidate_id")
    summary = pd.read_csv(discovery_dir / "discovery_summary.csv")
    correlations = pd.read_csv(discovery_dir / "discovery_correlations.csv")
    failures = json.loads((discovery_dir / "failures.json").read_text(encoding="utf-8"))
    if len(proposal_by_id) != 40 or len(lint) != 40:
        raise RuntimeError("Pack finalization requires 40 proposals and 40 lint records")
    if summary["factor_id"].nunique() + len(failures) != 40:
        raise RuntimeError("Discovery results do not account for all 40 proposals")

    correlation_lookup: dict[tuple[str, str], float] = {}
    for _, row in correlations.iterrows():
        left, right = str(row["left_factor_id"]), str(row["right_factor_id"])
        value = float(row["average_abs_daily_spearman"])
        correlation_lookup[(left, right)] = value
        correlation_lookup[(right, left)] = value

    eligible = summary.loc[summary["discovery_tier"].isin(ELIGIBLE_TIERS)].copy()
    ordered_ids = sorted(
        eligible["factor_id"].astype(str).tolist(),
        key=lambda factor_id: priority(eligible.loc[eligible["factor_id"].eq(factor_id)].iloc[0]),
    )
    retained: list[str] = []
    family_counts: Counter[str] = Counter()
    blocked_by: dict[str, str] = {}
    for factor_id in ordered_ids:
        family = str(proposal_by_id[factor_id]["economic_family"])
        if family_counts[family] >= args.family_cap:
            blocked_by[factor_id] = "family_cap"
            continue
        blockers = [
            (kept, correlation_lookup.get((factor_id, kept), float("nan")))
            for kept in retained
            if correlation_lookup.get((factor_id, kept), float("nan")) >= args.correlation_threshold
        ]
        if blockers:
            blocker, value = max(blockers, key=lambda item: item[1])
            blocked_by[factor_id] = f"correlated_with:{blocker}:{value:.6f}"
            continue
        retained.append(factor_id)
        family_counts[family] += 1

    summary_by_id = summary.set_index("factor_id")
    failure_by_id = {record["factor_id"]: record["error"] for record in failures}
    metric_rows: list[dict[str, Any]] = []
    trajectory_rows: list[dict[str, Any]] = []
    for record in proposals:
        factor_id = record["candidate_id"]
        lint_row = lint.loc[factor_id]
        if factor_id in summary_by_id.index:
            metrics = summary_by_id.loc[factor_id].to_dict()
            tier = str(metrics["discovery_tier"])
            if tier == "invalid":
                outcome = "invalid"
            elif factor_id in retained:
                outcome = tier
            elif tier in ELIGIBLE_TIERS:
                outcome = "duplicate_or_family_capped"
            else:
                outcome = "discovery_fail"
        else:
            metrics = {}
            tier = "invalid"
            outcome = "invalid"
        compact = {
            **record,
            **{key: json_safe(value) for key, value in metrics.items() if key != "factor_id"},
            "lint_status": lint_row["status"],
            "lint_errors": None if pd.isna(lint_row["errors"]) else str(lint_row["errors"]),
            "discovery_outcome": outcome,
            "independent_survivor": factor_id in retained,
            "dedup_reason": blocked_by.get(factor_id),
            "evaluation_error": failure_by_id.get(factor_id),
        }
        metric_rows.append(compact)
        trajectory_rows.append(
            {
                "campaign_version": campaign["campaign_version"],
                "campaign_hash": campaign["campaign_hash"],
                "pack_number": int(pack["pack_number"]),
                "candidate_id": factor_id,
                "factor_name": record["factor_name"],
                "formula": record["formula"],
                "formula_hash": pack["candidate_formula_hashes"][factor_id],
                "economic_hypothesis": record["economic_hypothesis"],
                "economic_family": record["economic_family"],
                "data_domain": record["data_domain"],
                "target_patterns": record["target_patterns"],
                "internal_sub_batch": int(record["internal_sub_batch"]),
                "lint_status": lint_row["status"],
                "discovery_outcome": outcome,
                "independent_survivor": factor_id in retained,
                "dedup_reason": blocked_by.get(factor_id),
                "metrics": {key: json_safe(value) for key, value in metrics.items()},
                "evaluation_error": failure_by_id.get(factor_id),
                "validation_labels_opened": False,
            }
        )

    metrics_frame = pd.DataFrame(metric_rows)
    metrics_path = pack_path.parent / "discovery_metrics.csv"
    metrics_frame.to_csv(metrics_path, index=False, mode="x")
    trajectory_text = "".join(
        json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
        for record in trajectory_rows
    )
    trajectory_append_path = pack_path.parent / "trajectory_append.jsonl"
    write_text_exclusive(trajectory_append_path, trajectory_text)
    existing_ids: set[str] = set()
    if campaign_trajectory_path.exists():
        existing_ids = {
            json.loads(line)["candidate_id"]
            for line in campaign_trajectory_path.read_text(encoding="utf-8").splitlines()
            if line
        }
    duplicates = existing_ids & set(proposal_by_id)
    if duplicates:
        raise RuntimeError(f"Candidate IDs already exist in campaign trajectory: {sorted(duplicates)}")
    if campaign_trajectory_path.exists():
        with campaign_trajectory_path.open("a", encoding="utf-8") as handle:
            handle.write(trajectory_text)
    else:
        write_text_exclusive(campaign_trajectory_path, trajectory_text)

    memory = json.loads(memory_path.read_text(encoding="utf-8"))
    prior_patterns = {
        record["pattern"]: record
        for group in ("success_patterns", "forbidden_regions")
        for record in memory.get(group, [])
    }
    pattern_stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "pack_attempt_count": 0,
            "pack_valid_count": 0,
            "pack_discovery_research_count": 0,
            "pack_discovery_qualified_count": 0,
            "pack_independent_survivor_count": 0,
            "correlations": [],
        }
    )
    for row in trajectory_rows:
        for pattern in row["target_patterns"]:
            stats = pattern_stats[str(pattern)]
            stats["pack_attempt_count"] += 1
            stats["pack_valid_count"] += int(row["discovery_outcome"] != "invalid")
            stats["pack_discovery_research_count"] += int(row["discovery_outcome"] == "discovery_research")
            stats["pack_discovery_qualified_count"] += int(
                row["discovery_outcome"] in {"discovery_qualified", "discovery_implementation"}
            )
            stats["pack_independent_survivor_count"] += int(row["independent_survivor"])
            corr = row["metrics"].get("max_abs_batch_correlation")
            if corr is not None:
                stats["correlations"].append(float(corr))
    pattern_records = []
    for pattern, stats in sorted(pattern_stats.items()):
        correlations_for_pattern = stats.pop("correlations")
        pattern_records.append(
            {
                "pattern": pattern,
                **stats,
                "pack_p75_max_correlation": (
                    float(np.quantile(correlations_for_pattern, 0.75))
                    if correlations_for_pattern
                    else None
                ),
                "prior_legacy_state": prior_patterns.get(pattern),
                "formal_quality_scores_available": False,
                "red_sea_classification": "deferred_until_complete_formal_scores",
                "state_action": "no_change",
            }
        )
    pattern_state = {
        "campaign_version": campaign["campaign_version"],
        "pack_number": int(pack["pack_number"]),
        "updated_once_after_all_40_outcomes": True,
        "proposal_count": 40,
        "validation_labels_opened": False,
        "input_experience_memory": str(memory_path),
        "input_experience_memory_sha256": sha256_file(memory_path),
        "formal_quality_scores_available": False,
        "red_sea_formula_applied": False,
        "reason": "Red Sea pass/admission statistics require complete formal scores; discovery diagnostics are not substituted.",
        "patterns": pattern_records,
    }
    pattern_state_path = pack_path.parent / "pattern_state_after_pack.json"
    write_text_exclusive(
        pattern_state_path,
        json.dumps(pattern_state, ensure_ascii=False, indent=2) + "\n",
    )

    tier_counts = summary["discovery_tier"].value_counts().to_dict()
    domain_yield = metrics_frame.groupby("data_domain").agg(
        proposals=("candidate_id", "size"),
        research_or_better=("discovery_outcome", lambda values: values.isin(ELIGIBLE_TIERS).sum()),
        independent_survivors=("independent_survivor", "sum"),
    )
    family_yield = metrics_frame.groupby("economic_family").agg(
        proposals=("candidate_id", "size"),
        research_or_better=("discovery_outcome", lambda values: values.isin(ELIGIBLE_TIERS).sum()),
        independent_survivors=("independent_survivor", "sum"),
    )
    lines = [
        f"# {campaign['campaign_version']} Pack {int(pack['pack_number']):02d}",
        "",
        f"- Proposals: 40",
        f"- Lint valid / invalid: {int(lint['status'].eq('valid').sum())} / {int(lint['status'].ne('valid').sum())}",
        f"- Evaluation failures: {len(failures)}",
        f"- Discovery qualified: {tier_counts.get('discovery_qualified', 0) + tier_counts.get('discovery_implementation', 0)}",
        f"- Discovery research: {tier_counts.get('discovery_research', 0)}",
        f"- Discovery fail: {tier_counts.get('discovery_fail', 0)}",
        f"- Discovery invalid: {tier_counts.get('invalid', 0)}",
        f"- Greedy independent survivors at |rho| < {args.correlation_threshold:.2f}: {len(retained)}",
        "- Validation labels opened: no",
        "- Red Sea update: formal classification deferred; attempt/yield diagnostics recorded once",
        "",
        "## Data-domain yield",
        "",
        domain_yield.to_markdown(),
        "",
        "## Economic-family yield",
        "",
        family_yield.to_markdown(),
        "",
        "## Independent survivors",
        "",
    ]
    for factor_id in retained:
        row = summary_by_id.loc[factor_id]
        lines.append(
            f"- `{factor_id}` {row['factor_name']}: tier={row['discovery_tier']}, "
            f"IC={row['discovery_rank_ic']:.4f}, NW={row['newey_west_t']:.2f}, "
            f"net10={row['net_sharpe_10bps']:.2f}"
        )
    summary_path = pack_path.parent / "pack_summary.md"
    write_text_exclusive(summary_path, "\n".join(lines) + "\n")
    report = {
        "campaign_version": campaign["campaign_version"],
        "pack_number": int(pack["pack_number"]),
        "status": "discovery_pack_complete_validation_sealed",
        "proposal_count": 40,
        "independent_survivor_count": len(retained),
        "independent_survivor_ids": retained,
        "validation_labels_opened": False,
        "artifacts": {
            "discovery_metrics": {"path": str(metrics_path), "sha256": sha256_file(metrics_path)},
            "pack_summary": {"path": str(summary_path), "sha256": sha256_file(summary_path)},
            "trajectory_append": {"path": str(trajectory_append_path), "sha256": sha256_file(trajectory_append_path)},
            "pattern_state_after_pack": {"path": str(pattern_state_path), "sha256": sha256_file(pattern_state_path)},
        },
    }
    report_path = pack_path.parent / "pack_report.json"
    write_text_exclusive(report_path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
