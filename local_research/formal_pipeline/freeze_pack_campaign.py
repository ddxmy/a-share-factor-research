#!/usr/bin/env python3
"""Globally deduplicate a completed Pack-40 campaign before validation.

The program accepts only a complete campaign of sealed Pack-40 artifacts.  It
uses the discovery panel (2016-2020 labels) to recompute one cross-pack signal
correlation matrix, then freezes an auditable candidate set.  It never reads
factor-validation, synthesis-validation, or lockbox observations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
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
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def write_json_exclusive(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def finite_float(value: Any, fallback: float = -math.inf) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    return number if math.isfinite(number) else fallback


def priority_tuple(row: pd.Series) -> tuple[Any, ...]:
    return (
        -ELIGIBLE_TIERS[str(row["discovery_tier"])],
        -finite_float(row.get("discovery_rank_ic")),
        -finite_float(row.get("newey_west_t")),
        -finite_float(row.get("net_sharpe_10bps")),
        str(row["factor_id"]),
    )


def average_absolute_daily_spearman(signals: dict[str, pd.Series]) -> pd.DataFrame:
    ids = sorted(signals)
    wide = pd.concat({factor_id: signals[factor_id] for factor_id in ids}, axis=1)
    sums = np.zeros((len(ids), len(ids)), dtype=np.float64)
    counts = np.zeros((len(ids), len(ids)), dtype=np.int32)
    for _, day in wide.groupby(level="dt", sort=True):
        corr = day.corr(method="spearman", min_periods=30).abs().to_numpy(dtype=float)
        valid = np.isfinite(corr)
        sums[valid] += corr[valid]
        counts[valid] += 1
    average = np.divide(sums, counts, out=np.full_like(sums, np.nan), where=counts > 0)
    np.fill_diagonal(average, 1.0)
    return pd.DataFrame(average, index=ids, columns=ids)


def load_complete_campaign(
    campaign: dict[str, Any],
    campaign_dir: Path,
    results_root: Path,
) -> tuple[pd.DataFrame, dict[str, dict[str, Any]], list[dict[str, Any]]]:
    maximum_packs = int(campaign["budgets"]["maximum_packs"])
    pack_size = int(campaign["budgets"]["pack_size"])
    summaries: list[pd.DataFrame] = []
    proposals: dict[str, dict[str, Any]] = {}
    bindings: list[dict[str, Any]] = []

    for pack_number in range(1, maximum_packs + 1):
        pack_dir = campaign_dir / f"pack_{pack_number:02d}"
        result_dir = results_root / f"pack_{pack_number:02d}_discovery"
        paths = {
            "pack_manifest": pack_dir / "pack_manifest.json",
            "pack_report": pack_dir / "pack_report.json",
            "proposals": pack_dir / "proposals.json",
            "parameter_plan": pack_dir / "parameter_plan.json",
            "lint_results": pack_dir / "lint_results.csv",
            "discovery_summary": result_dir / "discovery_summary.csv",
            "discovery_run": result_dir / "run_manifest.json",
            "discovery_failures": result_dir / "failures.json",
        }
        missing = [str(path) for path in paths.values() if not path.exists()]
        if missing:
            raise RuntimeError(f"Incomplete pack {pack_number}: {missing}")

        manifest = json.loads(paths["pack_manifest"].read_text(encoding="utf-8"))
        report = json.loads(paths["pack_report"].read_text(encoding="utf-8"))
        run = json.loads(paths["discovery_run"].read_text(encoding="utf-8"))
        if manifest.get("status") != "sealed_before_discovery":
            raise RuntimeError(f"Pack {pack_number} was not sealed before discovery")
        if manifest.get("campaign_hash") != campaign["campaign_hash"]:
            raise RuntimeError(f"Pack {pack_number} campaign hash mismatch")
        if report.get("status") != "discovery_pack_complete_validation_sealed":
            raise RuntimeError(f"Pack {pack_number} is not discovery-complete")
        if report.get("validation_labels_opened") is not False:
            raise RuntimeError(f"Pack {pack_number} report opened validation labels")
        if run.get("campaign_hash") != campaign["campaign_hash"]:
            raise RuntimeError(f"Pack {pack_number} discovery run hash mismatch")
        if run.get("validation_labels_opened") is not False:
            raise RuntimeError(f"Pack {pack_number} discovery run opened validation labels")
        if run.get("metadata_read_end") != str(DISCOVERY_END.date()):
            raise RuntimeError(f"Pack {pack_number} has unexpected discovery end")
        if sha256_file(paths["proposals"]) != manifest["proposals_sha256"]:
            raise RuntimeError(f"Pack {pack_number} proposals changed after seal")
        if sha256_file(paths["parameter_plan"]) != manifest["parameter_plan_sha256"]:
            raise RuntimeError(f"Pack {pack_number} parameter plan changed after seal")
        if sha256_file(paths["lint_results"]) != run["lint_results_sha256"]:
            raise RuntimeError(f"Pack {pack_number} lint results changed after discovery")

        proposal_payload = json.loads(paths["proposals"].read_text(encoding="utf-8"))
        proposal_rows = proposal_payload.get("proposals", proposal_payload)
        if len(proposal_rows) != pack_size:
            raise RuntimeError(f"Pack {pack_number} does not contain {pack_size} proposals")
        for proposal in proposal_rows:
            factor_id = str(proposal["candidate_id"])
            if factor_id in proposals:
                raise RuntimeError(f"Duplicate candidate across packs: {factor_id}")
            proposals[factor_id] = proposal

        plan_payload = json.loads(paths["parameter_plan"].read_text(encoding="utf-8"))
        if isinstance(plan_payload.get("factors"), dict):
            plan = plan_payload["factors"]
        else:
            plan_rows = plan_payload.get("parameters", plan_payload.get("parameter_plans", []))
            plan = {str(row["candidate_id"]): row for row in plan_rows}
        if len(plan) != pack_size or set(plan) != {
            str(row["candidate_id"]) for row in proposal_rows
        }:
            raise RuntimeError(f"Pack {pack_number} parameter plan is not exact")
        for factor_id, specification in plan.items():
            parameter_free = specification.get("parameter_free") is True
            variants = specification.get("formula_variants", [])
            if parameter_free == bool(variants):
                raise RuntimeError(f"Invalid parameter declaration for {factor_id}")
            variant_names = [row.get("variant_name") for row in variants]
            variant_formulas = [row.get("formula") for row in variants]
            if (
                None in variant_names
                or None in variant_formulas
                or len(variant_names) != len(set(variant_names))
            ):
                raise RuntimeError(f"Invalid parameter variants for {factor_id}")

        summary = pd.read_csv(paths["discovery_summary"])
        failures = json.loads(paths["discovery_failures"].read_text(encoding="utf-8"))
        summary_ids = set(summary["factor_id"].astype(str))
        failure_ids = {str(record["factor_id"]) for record in failures}
        proposal_ids = {str(row["candidate_id"]) for row in proposal_rows}
        if summary_ids & failure_ids or summary_ids | failure_ids != proposal_ids:
            raise RuntimeError(f"Pack {pack_number} discovery outcomes are not exact")
        if len(summary_ids) + len(failures) != pack_size:
            raise RuntimeError(f"Pack {pack_number} does not account for all proposals")
        if failures:
            failure_rows = pd.DataFrame(
                [
                    {
                        "factor_id": factor_id,
                        "factor_name": proposals[factor_id]["factor_name"],
                        "discovery_tier": "invalid",
                        "discovery_screen_failures": "evaluation_error",
                        "evaluation_error": record.get("error"),
                    }
                    for record in failures
                    for factor_id in [str(record["factor_id"])]
                ]
            )
            summary = pd.concat([summary, failure_rows], ignore_index=True, sort=False)
        summary["pack_number"] = pack_number
        summaries.append(summary)
        bindings.append(
            {
                "pack_number": pack_number,
                **{name: {"path": str(path), "sha256": sha256_file(path)} for name, path in paths.items()},
            }
        )

    combined = pd.concat(summaries, ignore_index=True)
    expected = int(campaign["budgets"]["candidate_budget"])
    if len(combined) != expected or combined["factor_id"].nunique() != expected:
        raise RuntimeError(f"Expected exactly {expected} unique completed candidates")
    if set(combined["factor_id"].astype(str)) != set(proposals):
        raise RuntimeError("Discovery summaries and proposal manifests disagree")
    return combined, proposals, bindings


def load_consolidated_parameter_plan(
    path: Path,
    campaign: dict[str, Any],
    proposals: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") != "consolidated_from_sealed_pack_plans":
        raise RuntimeError("Campaign parameter plan is not a sealed-plan consolidation")
    if payload.get("campaign_hash") != campaign["campaign_hash"]:
        raise RuntimeError("Campaign parameter plan hash binding differs")
    if payload.get("validation_labels_opened") is not False:
        raise RuntimeError("Campaign parameter plan reports opened validation labels")
    records = payload.get("parameter_plans", [])
    by_id = {str(record.get("candidate_id")): record for record in records}
    if len(records) != len(by_id) or set(by_id) != set(proposals):
        raise RuntimeError("Campaign parameter plan must cover all proposals exactly once")
    return by_id


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", required=True)
    parser.add_argument("--campaign-manifest", required=True)
    parser.add_argument("--campaign-dir", required=True)
    parser.add_argument("--results-root", required=True)
    parser.add_argument("--script-version", required=True)
    parser.add_argument("--parameter-plan", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--correlation-threshold", type=float, default=0.50)
    parser.add_argument("--family-cap", type=int, default=3)
    parser.add_argument("--maximum-frozen", type=int, default=25)
    parser.add_argument("--minimum-frozen", type=int, default=12)
    args = parser.parse_args()

    panel_path = Path(args.panel).resolve()
    campaign_path = Path(args.campaign_manifest).resolve()
    campaign_dir = Path(args.campaign_dir).resolve()
    results_root = Path(args.results_root).resolve()
    script_dir = (PROJECT_ROOT / "factor_script" / args.script_version).resolve()
    parameter_plan_path = Path(args.parameter_plan).resolve()
    output_dir = Path(args.output_dir).resolve()
    if output_dir.exists():
        raise FileExistsError(output_dir)

    campaign = json.loads(campaign_path.read_text(encoding="utf-8"))
    panel_manifest_path = panel_path.with_suffix(".manifest.json")
    panel_manifest = json.loads(panel_manifest_path.read_text(encoding="utf-8"))
    if campaign.get("status") != "discovery_open_validation_sealed":
        raise RuntimeError("Campaign is not open with validation sealed")
    freeze_targets = campaign["freeze_targets"]
    if not math.isclose(args.correlation_threshold, 0.50, rel_tol=0.0, abs_tol=1e-12):
        raise RuntimeError("Campaign protocol fixes cross-pack correlation threshold at 0.50")
    if args.family_cap != int(freeze_targets["maximum_per_family_or_cluster"]):
        raise RuntimeError("--family-cap must match the pre-registered campaign target")
    if args.minimum_frozen != int(freeze_targets["minimum_frozen_candidates"]):
        raise RuntimeError("--minimum-frozen must match the pre-registered campaign target")
    if args.maximum_frozen != int(freeze_targets["target_frozen_candidates"][1]):
        raise RuntimeError("--maximum-frozen must match the pre-registered campaign target")
    if campaign.get("discovery_panel_sha256") != sha256_file(panel_path):
        raise RuntimeError("Discovery panel changed after campaign registration")
    if panel_manifest.get("research_stage") != "discovery":
        raise RuntimeError("Global freeze requires the discovery-only panel")
    if panel_manifest.get("output_sha256") != campaign["discovery_panel_sha256"]:
        raise RuntimeError("Panel manifest and campaign hashes differ")

    combined, proposals, pack_bindings = load_complete_campaign(
        campaign, campaign_dir, results_root
    )
    load_consolidated_parameter_plan(parameter_plan_path, campaign, proposals)
    eligible = combined.loc[combined["discovery_tier"].isin(ELIGIBLE_TIERS)].copy()
    eligible["economic_family"] = eligible["factor_id"].map(
        lambda factor_id: proposals[str(factor_id)]["economic_family"]
    )
    ordered_ids = sorted(
        eligible["factor_id"].astype(str).tolist(),
        key=lambda factor_id: priority_tuple(
            eligible.loc[eligible["factor_id"].astype(str).eq(factor_id)].iloc[0]
        ),
    )

    policy = {
        "campaign_version": campaign["campaign_version"],
        "campaign_hash": campaign["campaign_hash"],
        "stage": "cross_pack_discovery_global_dedup_before_validation",
        "visibility": "2016-2020 only; all later labels remain sealed",
        "candidate_budget_exhausted": len(proposals) == int(campaign["budgets"]["candidate_budget"]),
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
        "script_version": args.script_version,
        "parameter_plan": str(parameter_plan_path),
        "parameter_plan_sha256": sha256_file(parameter_plan_path),
        "freezer_path": str(Path(__file__).resolve()),
        "freezer_sha256": sha256_file(Path(__file__).resolve()),
        "pack_bindings": pack_bindings,
        "validation_labels_opened": False,
    }
    output_dir.mkdir(parents=True, exist_ok=False)
    policy_path = output_dir / "selection_policy.json"
    write_json_exclusive(policy_path, policy)

    records_by_id = {record["factor_id"]: record for record in load_factor_records(script_dir)}
    missing = sorted(set(ordered_ids) - set(records_by_id))
    if missing:
        raise RuntimeError(f"Missing eligible factor scripts: {missing}")

    metadata = load_discovery_metadata(panel_path)
    executor = FormulaExecutor(str(panel_path), start_date=20150101, end_date=20201231)
    signals: dict[str, pd.Series] = {}
    eligible_by_id = eligible.set_index("factor_id", drop=False)
    for position, factor_id in enumerate(ordered_ids, start=1):
        record = records_by_id[factor_id]
        proposal = proposals[factor_id]
        if record["formula_hash"] != hashlib.sha256(
            str(proposal["formula"]).encode("utf-8")
        ).hexdigest():
            raise RuntimeError(f"Formula hash mismatch for {factor_id}")
        signal = executor.compute(record["formula"])
        prepared = preprocess_discovery_signal(signal, metadata)
        direction = int(eligible_by_id.loc[factor_id, "train_direction"])
        signals[factor_id] = direction * prepared["neutral_signal"]
        print(f"[{position}/{len(ordered_ids)}] prepared {factor_id}", flush=True)

    matrix = average_absolute_daily_spearman(signals)
    matrix.to_csv(output_dir / "global_correlation_matrix.csv")
    pairs = [
        {
            "left_factor_id": left,
            "right_factor_id": right,
            "average_abs_daily_spearman": float(matrix.loc[left, right]),
        }
        for left_position, left in enumerate(matrix.index)
        for right in matrix.index[left_position + 1 :]
    ]
    pd.DataFrame(pairs).sort_values(
        "average_abs_daily_spearman", ascending=False
    ).to_csv(output_dir / "global_correlations.csv", index=False)

    retained: list[str] = []
    family_counts: Counter[str] = Counter()
    decisions: list[dict[str, Any]] = []
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
                "pack_number": int(row["pack_number"]),
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
    decision_frame.loc[decision_frame["decision"].eq("retain")].to_csv(
        output_dir / "frozen_candidates.csv", index=False
    )
    combined.to_csv(output_dir / "global_candidate_summary.csv", index=False)

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
                "pack_number": int(row["pack_number"]),
            }
        )
    status = (
        "formula_frozen_validation_sealed"
        if len(retained) >= args.minimum_frozen
        else "insufficient_yield_validation_sealed"
    )
    freeze_manifest = {
        "campaign_version": campaign["campaign_version"],
        "campaign_hash": campaign["campaign_hash"],
        "status": status,
        "candidate_budget_exhausted": True,
        "total_proposals": len(combined),
        "eligible_before_global_dedup": len(eligible),
        "frozen_candidate_count": len(retained),
        "formula_set_hash": canonical_json_hash(frozen_records),
        "selection_policy_sha256": sha256_file(policy_path),
        "parameter_plan": str(parameter_plan_path),
        "parameter_plan_sha256": sha256_file(parameter_plan_path),
        "data_snapshot": campaign["data_snapshot"],
        "panel_sha256": campaign["discovery_panel_sha256"],
        "pack_bindings": pack_bindings,
        "validation_labels_opened": False,
        "frozen_candidates": frozen_records,
    }
    write_json_exclusive(output_dir / "formula_freeze_manifest.json", freeze_manifest)
    print(
        f"Frozen {len(retained)} of {len(eligible)} discovery-eligible candidates; status={status}",
        flush=True,
    )


if __name__ == "__main__":
    main()
