#!/usr/bin/env python3
"""Canonical Red Sea saturation and persistent-low-yield metrics."""

from __future__ import annotations

import argparse
import json
from math import exp
from pathlib import Path
from typing import Any


def clip(value: float) -> float:
    return max(0.0, min(1.0, value))


def sigmoid(value: float) -> float:
    return 1.0 / (1.0 + exp(-value))


DEFAULTS = {
    "pass_threshold": 65.0,
    "corr_threshold": 0.50,
    "evidence_scale": 8.0,
    "success_scale": 1.5,
    "coverage_scale": 4.0,
    "corr_temp": 0.05,
    "yield_margin": 0.15,
    "yield_temp": 0.10,
    "score_delta": 5.0,
    "min_saturation_attempts": 16,
    "min_saturation_admitted": 3,
    "min_recent_attempts": 5,
    "min_recent_pass": 2,
    "min_low_yield_attempts": 16,
    "deprioritize_threshold": 0.45,
    "restrict_threshold": 0.60,
    "forbidden_threshold": 0.70,
}


def load_json_argument(value: str) -> dict[str, Any]:
    """Load an inline JSON object or a JSON file without stat-ing long JSON text."""
    stripped = value.lstrip()
    if stripped.startswith("{"):
        return json.loads(value)
    return json.loads(Path(value).read_text(encoding="utf-8"))


def compute_saturation(stats: dict[str, Any], params: dict[str, float] | None = None) -> float:
    p = {**DEFAULTS, **(params or {})}
    attempts = float(stats.get("attempt_count", 0))
    admitted = float(stats.get("admitted_count", 0))
    passed = float(stats.get("pass_count", 0))
    recent_passed = float(stats.get("recent_pass_count", 0))
    recent_admitted = float(stats.get("recent_admitted_count", 0))
    recent_corr = float(stats.get("recent_p75_max_corr", 0))
    historical_best = float(stats.get("historical_best_before_recent", 0))
    recent_best = float(stats.get("recent_best_score", 0))

    evidence = 1.0 - exp(-attempts / p["evidence_scale"])
    success_gate = 1.0 - exp(-admitted / p["success_scale"])
    coverage = 1.0 - exp(-admitted / p["coverage_scale"])
    corr_pressure = sigmoid((recent_corr - p["corr_threshold"]) / p["corr_temp"])
    historical_yield = admitted / max(passed, 1.0)
    recent_yield = recent_admitted / max(recent_passed, 1.0)
    novelty_decay = sigmoid(
        (historical_yield - recent_yield - p["yield_margin"]) / p["yield_temp"]
    )
    improvement = max(0.0, recent_best - historical_best)
    score_plateau = exp(-improvement / p["score_delta"])
    diminishing_return = 0.5 * novelty_decay + 0.5 * score_plateau
    core_saturation = corr_pressure * diminishing_return
    return clip(
        evidence * success_gate * (
            0.75 * core_saturation + 0.25 * coverage * corr_pressure
        )
    )


def compute_low_yield(stats: dict[str, Any], params: dict[str, float] | None = None) -> float:
    p = {**DEFAULTS, **(params or {})}
    attempts = float(stats.get("attempt_count", 0))
    passed = float(stats.get("pass_count", 0))
    admitted = float(stats.get("admitted_count", 0))
    avg_score = float(stats.get("avg_score", 0))
    evidence = 1.0 - exp(-attempts / p["evidence_scale"])
    no_success_gate = exp(-admitted / p["success_scale"])
    pass_rate = (passed + 1.0) / (attempts + 2.0)
    pass_failure = 1.0 - pass_rate
    score_deficit = clip((p["pass_threshold"] - avg_score) / p["pass_threshold"])
    return clip(evidence * no_success_gate * (0.65 * pass_failure + 0.35 * score_deficit))


def classify_pattern(stats: dict[str, Any], params: dict[str, float] | None = None) -> dict[str, Any]:
    p = {**DEFAULTS, **(params or {})}
    saturation = compute_saturation(stats, p)
    low_yield = compute_low_yield(stats, p)
    sat_forbidden = (
        saturation >= p["forbidden_threshold"]
        and stats.get("attempt_count", 0) >= p["min_saturation_attempts"]
        and stats.get("admitted_count", 0) >= p["min_saturation_admitted"]
        and stats.get("recent_attempt_count", 0) >= p["min_recent_attempts"]
        and stats.get("recent_pass_count", 0) >= p["min_recent_pass"]
    )
    low_forbidden = (
        low_yield >= p["forbidden_threshold"]
        and stats.get("attempt_count", 0) >= p["min_low_yield_attempts"]
        and stats.get("admitted_count", 0) == 0
    )
    if sat_forbidden:
        status, reason = "forbidden", "saturated_high_corr"
    elif low_forbidden:
        status, reason = "forbidden", "persistent_low_score"
    elif max(saturation, low_yield) >= p["restrict_threshold"]:
        status, reason = "restricted", None
    elif max(saturation, low_yield) >= p["deprioritize_threshold"]:
        status, reason = "deprioritize", None
    else:
        status, reason = "active", None
    return {
        "saturation_score": saturation,
        "low_yield_score": low_yield,
        "status": status,
        "forbidden_reason": reason,
        "red_sea": reason == "saturated_high_corr",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify one pattern-stat JSON object")
    parser.add_argument("stats_json", help="JSON object or JSON file path")
    args = parser.parse_args()
    stats = load_json_argument(args.stats_json)
    print(json.dumps(classify_pattern(stats), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
