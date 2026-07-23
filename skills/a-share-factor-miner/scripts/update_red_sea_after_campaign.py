#!/usr/bin/env python3
"""Compute Red Sea and low-yield memory from a completed formal campaign."""

from __future__ import annotations

import argparse
import json
import math
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PASS_THRESHOLD = 65.0
CORR_THRESHOLD = 0.50
EVIDENCE_SCALE = 8.0
SUCCESS_SCALE = 1.5
COVERAGE_SCALE = 4.0
CORR_TEMP = 0.05
YIELD_MARGIN = 0.15
YIELD_TEMP = 0.10
SCORE_DELTA = 5.0
RECENT_WINDOW = 20
MIN_SATURATION_ATTEMPTS = 16
MIN_SATURATION_ADMITTED = 3
MIN_RECENT_ATTEMPTS = 5
MIN_RECENT_PASS = 2
MIN_LOW_YIELD_ATTEMPTS = 16
DEPRIORITIZE_THRESHOLD = 0.45
RESTRICT_THRESHOLD = 0.60
FORBIDDEN_THRESHOLD = 0.70


def sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def clip(value: float) -> float:
    return min(max(value, 0.0), 1.0)


def finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def write_json_exclusive(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-trajectory", required=True)
    parser.add_argument("--complete-summary", required=True)
    parser.add_argument("--campaign-manifest", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    trajectory_path = Path(args.candidate_trajectory).resolve()
    summary_path = Path(args.complete_summary).resolve()
    campaign_path = Path(args.campaign_manifest).resolve()
    trajectory = [
        json.loads(line)
        for line in trajectory_path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    campaign = json.loads(campaign_path.read_text(encoding="utf-8"))
    summary = pd.read_csv(summary_path).set_index("factor_id")
    expected = int(campaign["budgets"]["candidate_budget"])
    if len(trajectory) != expected or len({row["candidate_id"] for row in trajectory}) != expected:
        raise RuntimeError("Candidate trajectory is not the complete unique campaign")
    if any(row.get("validation_labels_opened") is not False for row in trajectory):
        raise RuntimeError("Discovery trajectory visibility audit failed")

    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in trajectory:
        by_family[str(row["economic_family"])].append(row)
    pattern_rows = []
    for family, attempts in sorted(by_family.items()):
        recent = attempts[-RECENT_WINDOW:]
        scored = []
        passes = []
        admitted = []
        for row in attempts:
            factor_id = row["candidate_id"]
            if factor_id not in summary.index:
                continue
            result = summary.loc[factor_id]
            if finite(result.get("formal_quality_score")):
                scored.append(float(result["formal_quality_score"]))
            is_pass = bool(
                finite(result.get("formal_quality_score"))
                and float(result["formal_quality_score"]) >= PASS_THRESHOLD
                and result["decision"] in {"admit", "replace"}
            )
            passes.append((factor_id, is_pass))
            admitted.append((factor_id, result["decision"] in {"admit", "replace"}))

        recent_ids = {row["candidate_id"] for row in recent}
        recent_pass_count = sum(flag for factor_id, flag in passes if factor_id in recent_ids)
        recent_admitted_count = sum(
            flag for factor_id, flag in admitted if factor_id in recent_ids
        )
        pass_count = sum(flag for _, flag in passes)
        admitted_count = sum(flag for _, flag in admitted)
        recent_scores = [
            float(summary.loc[factor_id, "formal_quality_score"])
            for factor_id in recent_ids & set(summary.index)
            if finite(summary.loc[factor_id, "formal_quality_score"])
        ]
        historical_ids = {row["candidate_id"] for row in attempts[:-RECENT_WINDOW]}
        historical_scores = [
            float(summary.loc[factor_id, "formal_quality_score"])
            for factor_id in historical_ids & set(summary.index)
            if finite(summary.loc[factor_id, "formal_quality_score"])
        ]
        recent_correlations = [
            float(row.get("metrics", {}).get("max_abs_batch_correlation"))
            for row in recent
            if finite(row.get("metrics", {}).get("max_abs_batch_correlation"))
        ]

        evidence = 1.0 - math.exp(-len(attempts) / EVIDENCE_SCALE)
        success_gate = 1.0 - math.exp(-admitted_count / SUCCESS_SCALE)
        coverage = 1.0 - math.exp(-admitted_count / COVERAGE_SCALE)
        recent_p75_corr = (
            float(np.quantile(recent_correlations, 0.75)) if recent_correlations else None
        )
        corr_pressure = (
            sigmoid((recent_p75_corr - CORR_THRESHOLD) / CORR_TEMP)
            if recent_p75_corr is not None
            else None
        )
        historical_yield = admitted_count / max(pass_count, 1)
        recent_yield = recent_admitted_count / max(recent_pass_count, 1)
        novelty_decay = sigmoid((historical_yield - recent_yield - YIELD_MARGIN) / YIELD_TEMP)
        recent_best = max(recent_scores) if recent_scores else None
        historical_best = max(historical_scores) if historical_scores else None
        if recent_best is None:
            improvement = 0.0
        elif historical_best is None:
            improvement = recent_best
        else:
            improvement = max(0.0, recent_best - historical_best)
        score_plateau = math.exp(-improvement / SCORE_DELTA)
        if corr_pressure is None:
            saturation_score = None
        else:
            diminishing_return = 0.5 * novelty_decay + 0.5 * score_plateau
            core_saturation = corr_pressure * diminishing_return
            saturation_score = clip(
                evidence
                * success_gate
                * (0.75 * core_saturation + 0.25 * coverage * corr_pressure)
            )

        avg_score = float(np.mean(scored)) if scored else None
        if avg_score is None:
            low_yield_score = None
        else:
            no_success_gate = math.exp(-admitted_count / SUCCESS_SCALE)
            pass_rate = (pass_count + 1) / (len(attempts) + 2)
            pass_failure = 1.0 - pass_rate
            score_deficit = clip((PASS_THRESHOLD - avg_score) / PASS_THRESHOLD)
            low_yield_score = clip(
                evidence * no_success_gate * (0.65 * pass_failure + 0.35 * score_deficit)
            )

        saturation_forbidden = bool(
            saturation_score is not None
            and saturation_score >= FORBIDDEN_THRESHOLD
            and len(attempts) >= MIN_SATURATION_ATTEMPTS
            and admitted_count >= MIN_SATURATION_ADMITTED
            and len(recent) >= MIN_RECENT_ATTEMPTS
            and recent_pass_count >= MIN_RECENT_PASS
        )
        low_yield_forbidden = bool(
            low_yield_score is not None
            and low_yield_score >= FORBIDDEN_THRESHOLD
            and len(attempts) >= MIN_LOW_YIELD_ATTEMPTS
            and admitted_count == 0
        )
        maximum = max(
            value for value in (saturation_score, low_yield_score, 0.0) if value is not None
        )
        if saturation_forbidden:
            action, reason = "forbidden", "saturated_high_corr"
        elif low_yield_forbidden:
            action, reason = "forbidden", "persistent_low_score"
        elif maximum >= RESTRICT_THRESHOLD:
            action, reason = "restrict", "structural_novelty_required"
        elif maximum >= DEPRIORITIZE_THRESHOLD:
            action, reason = "deprioritize", "weak_or_crowded_evidence"
        else:
            action, reason = "normal_exploration", "below_action_threshold"

        pattern_rows.append(
            {
                "pattern": f"economic_family:{family}",
                "economic_family": family,
                "attempt_count": len(attempts),
                "formal_score_count": len(scored),
                "pass_count": pass_count,
                "admitted_count": admitted_count,
                "avg_score": avg_score,
                "best_score": max(scored) if scored else None,
                "recent_attempt_count": len(recent),
                "recent_pass_count": recent_pass_count,
                "recent_admitted_count": recent_admitted_count,
                "recent_p75_max_corr": recent_p75_corr,
                "historical_best_before_recent": historical_best,
                "recent_best_score": recent_best,
                "saturation_score": saturation_score,
                "low_yield_score": low_yield_score,
                "red_sea": saturation_forbidden,
                "low_yield_forbidden": low_yield_forbidden,
                "action": action,
                "reason": reason,
            }
        )

    payload = {
        "schema_version": "local_quality_memory_v1",
        "campaign_version": campaign["campaign_version"],
        "campaign_hash": campaign["campaign_hash"],
        "updated_at": pd.Timestamp.now(tz="Asia/Shanghai").isoformat(),
        "candidate_count": len(trajectory),
        "formal_validation_count": len(summary),
        "pass_threshold": PASS_THRESHOLD,
        "formula_source": "skills/a-share-factor-miner/references/red_sea_memory.md",
        "provisional_scores_counted": False,
        "discovery_tiers_substituted_for_scores": False,
        "patterns": pattern_rows,
    }
    write_json_exclusive(Path(args.output).resolve(), payload)
    print(json.dumps({"patterns": len(pattern_rows), "actions": pd.Series([r['action'] for r in pattern_rows]).value_counts().to_dict()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
