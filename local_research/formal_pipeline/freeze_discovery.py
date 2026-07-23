#!/usr/bin/env python3
"""Globally deduplicate discovery survivors and freeze a validation candidate set.

This program is discovery-only. It refuses to read observations after 2020-12-31
and writes the selection policy before computing the global correlation matrix.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from evaluate_factors import PROJECT_ROOT, FormulaExecutor, load_factor_records
from screen_discovery import DISCOVERY_END, load_discovery_metadata, preprocess_discovery_signal


ELIGIBLE_TIERS = {
    "discovery_research": 1,
    "discovery_qualified": 2,
    "discovery_implementation": 3,
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_discovery_candidates(discovery_root: Path) -> tuple[pd.DataFrame, dict[str, dict[str, Any]]]:
    summaries: list[pd.DataFrame] = []
    proposals: dict[str, dict[str, Any]] = {}
    for batch in range(1, 13):
        batch_name = f"batch_{batch:02d}"
        batch_dir = discovery_root / batch_name
        run_path = batch_dir / "run_manifest.json"
        summary_path = batch_dir / "discovery_summary.csv"
        proposal_path = discovery_root / f"{batch_name}_proposal_manifest.json"
        if not run_path.exists() or not summary_path.exists() or not proposal_path.exists():
            raise RuntimeError(f"Incomplete discovery batch: {batch_name}")
        run = json.loads(run_path.read_text(encoding="utf-8"))
        if run.get("validation_labels_opened") is not False:
            raise RuntimeError(f"Validation visibility violation in {run_path}")
        if run.get("metadata_read_end") != str(DISCOVERY_END.date()):
            raise RuntimeError(f"Unexpected discovery end in {run_path}")
        frame = pd.read_csv(summary_path)
        frame["batch"] = batch
        summaries.append(frame)
        proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
        if proposal.get("validation_labels_opened") is not False:
            raise RuntimeError(f"Validation visibility violation in {proposal_path}")
        for item in proposal["proposals"]:
            proposals[item["candidate_id"]] = item

    combined = pd.concat(summaries, ignore_index=True)
    if len(combined) != 120 or combined["factor_id"].nunique() != 120:
        raise RuntimeError("Expected exactly 120 unique discovery candidates")
    return combined, proposals


def average_absolute_daily_spearman(signals: dict[str, pd.Series]) -> pd.DataFrame:
    """Vectorized equivalent of averaging absolute per-date Spearman correlations."""
    ids = sorted(signals)
    wide = pd.concat({factor_id: signals[factor_id] for factor_id in ids}, axis=1)
    sums = np.zeros((len(ids), len(ids)), dtype=np.float64)
    counts = np.zeros((len(ids), len(ids)), dtype=np.int32)
    for _, day in wide.groupby(level="dt", sort=True):
        # Let pandas rerank on each pair's common observations. Ranking columns
        # once before pairwise deletion is only approximate when missingness differs.
        corr = day.corr(method="spearman", min_periods=30).abs().to_numpy(dtype=float)
        valid = np.isfinite(corr)
        sums[valid] += corr[valid]
        counts[valid] += 1
    average = np.divide(
        sums,
        counts,
        out=np.full_like(sums, np.nan),
        where=counts > 0,
    )
    np.fill_diagonal(average, 1.0)
    return pd.DataFrame(average, index=ids, columns=ids)


def priority_tuple(row: pd.Series) -> tuple[Any, ...]:
    return (
        -ELIGIBLE_TIERS[row["discovery_tier"]],
        -float(row["discovery_rank_ic"]),
        -float(row["newey_west_t"]) if math.isfinite(float(row["newey_west_t"])) else math.inf,
        -float(row["net_sharpe_10bps"]),
        str(row["factor_id"]),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", required=True)
    parser.add_argument("--campaign-manifest", required=True)
    parser.add_argument("--discovery-root", required=True)
    parser.add_argument("--parameter-plan", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--correlation-threshold", type=float, default=0.50)
    parser.add_argument("--family-cap", type=int, default=3)
    parser.add_argument("--maximum-frozen", type=int, default=25)
    parser.add_argument("--minimum-frozen", type=int, default=12)
    args = parser.parse_args()

    panel_path = Path(args.panel).resolve()
    campaign_path = Path(args.campaign_manifest).resolve()
    discovery_root = Path(args.discovery_root).resolve()
    parameter_plan_path = Path(args.parameter_plan).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=False)

    campaign = json.loads(campaign_path.read_text(encoding="utf-8"))
    panel_manifest_path = panel_path.with_suffix(".manifest.json")
    panel_manifest = json.loads(panel_manifest_path.read_text(encoding="utf-8"))
    if campaign.get("status") != "discovery_open_validation_sealed":
        raise RuntimeError("Campaign is not open with validation sealed")
    if campaign.get("discovery_panel_sha256") != sha256_file(panel_path):
        raise RuntimeError("Discovery panel changed after campaign registration")
    if campaign.get("discovery_panel_sha256") != panel_manifest.get("output_sha256"):
        raise RuntimeError("Panel manifest and campaign hashes differ")

    combined, proposals = load_discovery_candidates(discovery_root)
    eligible = combined.loc[combined["discovery_tier"].isin(ELIGIBLE_TIERS)].copy()
    eligible["economic_family"] = eligible["factor_id"].map(
        lambda factor_id: proposals[factor_id]["target_patterns"][0]
        if proposals[factor_id].get("target_patterns")
        else "unclassified"
    )
    ordered_ids = sorted(eligible["factor_id"].tolist(), key=lambda factor_id: priority_tuple(
        eligible.loc[eligible["factor_id"].eq(factor_id)].iloc[0]
    ))

    parameter_plan = json.loads(parameter_plan_path.read_text(encoding="utf-8"))
    if parameter_plan.get("campaign_version") != campaign["campaign_version"]:
        raise RuntimeError("Parameter plan and campaign versions differ")
    plan_factors = parameter_plan.get("factors", {})
    if set(plan_factors) != set(ordered_ids):
        raise RuntimeError("Parameter plan must cover every discovery-eligible candidate exactly")
    for factor_id, specification in plan_factors.items():
        parameter_free = specification.get("parameter_free") is True
        variants = specification.get("variants", [])
        if parameter_free == bool(variants):
            raise RuntimeError(
                f"{factor_id} must declare either parameter_free=true or a non-empty variant list"
            )
        if variants:
            names = [variant.get("variant") for variant in variants]
            formulas = [variant.get("formula") for variant in variants]
            if None in names or None in formulas or len(names) != len(set(names)):
                raise RuntimeError(f"Invalid parameter variants for {factor_id}")

    policy = {
        "campaign_version": campaign["campaign_version"],
        "campaign_hash": campaign["campaign_hash"],
        "stage": "discovery_global_dedup_before_validation",
        "visibility": "2016-2020 only; factor validation remains sealed",
        "eligible_tiers": list(ELIGIBLE_TIERS),
        "priority_order": [
            "tier: implementation > qualified > research",
            "discovery_rank_ic descending",
            "newey_west_t descending",
            "net_sharpe_10bps descending",
            "factor_id ascending",
        ],
        "correlation_metric": "mean absolute daily cross-sectional Spearman",
        "correlation_threshold": args.correlation_threshold,
        "family_cap": args.family_cap,
        "maximum_frozen": args.maximum_frozen,
        "minimum_frozen": args.minimum_frozen,
        "eligible_candidate_count": len(eligible),
        "ordered_candidate_ids": ordered_ids,
        "parameter_plan": str(parameter_plan_path),
        "parameter_plan_sha256": sha256_file(parameter_plan_path),
        "validation_labels_opened": False,
    }
    policy_path = output_dir / "selection_policy.json"
    policy_path.write_text(json.dumps(policy, ensure_ascii=False, indent=2), encoding="utf-8")

    records_by_id = {
        record["factor_id"]: record
        for record in load_factor_records(PROJECT_ROOT / "factor_script" / "V20260720_v2")
    }
    missing = sorted(set(ordered_ids) - set(records_by_id))
    if missing:
        raise RuntimeError(f"Missing frozen-candidate scripts: {missing}")

    metadata = load_discovery_metadata(panel_path)
    executor = FormulaExecutor(str(panel_path), start_date=20150101, end_date=20201231)
    signals: dict[str, pd.Series] = {}
    for position, factor_id in enumerate(ordered_ids, start=1):
        record = records_by_id[factor_id]
        proposal = proposals[factor_id]
        if record["formula_hash"] != proposal["formula_hash"]:
            raise RuntimeError(f"Formula hash mismatch for {factor_id}")
        signal = executor.compute(record["formula"])
        prepared = preprocess_discovery_signal(signal, metadata)
        direction = int(eligible.loc[eligible["factor_id"].eq(factor_id), "train_direction"].iloc[0])
        signals[factor_id] = direction * prepared["neutral_signal"]
        print(f"[{position}/{len(ordered_ids)}] prepared {factor_id}", flush=True)

    matrix = average_absolute_daily_spearman(signals)
    pairs: list[dict[str, Any]] = []
    for left_position, left_id in enumerate(matrix.index):
        for right_id in matrix.index[left_position + 1 :]:
            pairs.append(
                {
                    "left_factor_id": left_id,
                    "right_factor_id": right_id,
                    "average_abs_daily_spearman": float(matrix.loc[left_id, right_id]),
                }
            )
    pd.DataFrame(pairs).sort_values(
        "average_abs_daily_spearman", ascending=False
    ).to_csv(output_dir / "global_correlations.csv", index=False)

    retained: list[str] = []
    family_counts: Counter[str] = Counter()
    decisions: list[dict[str, Any]] = []
    eligible_by_id = eligible.set_index("factor_id", drop=False)
    for factor_id in ordered_ids:
        row = eligible_by_id.loc[factor_id]
        family = str(row["economic_family"])
        correlated = [
            (kept, float(matrix.loc[factor_id, kept]))
            for kept in retained
            if float(matrix.loc[factor_id, kept]) >= args.correlation_threshold
        ]
        if len(retained) >= args.maximum_frozen:
            decision, reason = "exclude", "maximum_frozen_reached"
        elif family_counts[family] >= args.family_cap:
            decision, reason = "exclude", "family_cap"
        elif correlated:
            blocker, rho = max(correlated, key=lambda item: item[1])
            decision, reason = "exclude", f"correlated_with:{blocker}:{rho:.6f}"
        else:
            decision, reason = "retain", "greedy_independent"
            retained.append(factor_id)
            family_counts[family] += 1
        decisions.append(
            {
                "factor_id": factor_id,
                "factor_name": row["factor_name"],
                "economic_family": family,
                "discovery_tier": row["discovery_tier"],
                "discovery_rank_ic": row["discovery_rank_ic"],
                "newey_west_t": row["newey_west_t"],
                "net_sharpe_10bps": row["net_sharpe_10bps"],
                "decision": decision,
                "reason": reason,
            }
        )
    decision_frame = pd.DataFrame(decisions)
    decision_frame.to_csv(output_dir / "dedup_decisions.csv", index=False)
    frozen = decision_frame.loc[decision_frame["decision"].eq("retain")].copy()
    frozen.to_csv(output_dir / "frozen_candidates.csv", index=False)

    frozen_records = []
    for factor_id in retained:
        record = records_by_id[factor_id]
        row = eligible_by_id.loc[factor_id]
        frozen_records.append(
            {
                "factor_id": factor_id,
                "factor_name": record["factor_name"],
                "formula": record["formula"],
                "formula_hash": record["formula_hash"],
                "train_direction": int(row["train_direction"]),
                "economic_family": row["economic_family"],
                "discovery_tier": row["discovery_tier"],
            }
        )
    formula_set_hash = canonical_json_hash(frozen_records)
    status = "formula_frozen_validation_sealed" if len(retained) >= args.minimum_frozen else "insufficient_yield"
    freeze_manifest = {
        "campaign_version": campaign["campaign_version"],
        "campaign_hash": campaign["campaign_hash"],
        "status": status,
        "candidate_budget_exhausted": True,
        "total_proposals": len(combined),
        "eligible_before_global_dedup": len(eligible),
        "frozen_candidate_count": len(retained),
        "formula_set_hash": formula_set_hash,
        "selection_policy_sha256": sha256_file(policy_path),
        "parameter_plan": str(parameter_plan_path),
        "parameter_plan_sha256": sha256_file(parameter_plan_path),
        "data_snapshot": campaign["data_snapshot"],
        "panel_sha256": campaign["discovery_panel_sha256"],
        "validation_labels_opened": False,
        "frozen_candidates": frozen_records,
    }
    (output_dir / "formula_freeze_manifest.json").write_text(
        json.dumps(freeze_manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    eligible.to_csv(output_dir / "global_candidate_summary.csv", index=False)
    print(
        f"Frozen {len(retained)} of {len(eligible)} discovery-eligible candidates; status={status}",
        flush=True,
    )


if __name__ == "__main__":
    main()
