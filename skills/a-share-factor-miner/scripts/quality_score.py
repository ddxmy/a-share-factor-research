#!/usr/bin/env python3
"""Deterministic transparent quality-score calculation."""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = SKILL_ROOT / "references" / "quality_score_v1.json"


def clip01(value: float) -> float:
    return max(0.0, min(1.0, value))


def load_config(path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_json_argument(value: str) -> dict[str, Any]:
    """Load an inline JSON object or a JSON file without stat-ing long JSON text."""
    stripped = value.lstrip()
    if stripped.startswith("{"):
        return json.loads(value)
    return json.loads(Path(value).read_text(encoding="utf-8"))


def metric_points(value: float, spec: dict[str, Any]) -> float:
    low = float(spec["low"])
    high = float(spec["high"])
    if high <= low:
        raise ValueError(f"Invalid bounds for {spec['name']}: low={low}, high={high}")
    scaled = clip01((float(value) - low) / (high - low))
    if spec["direction"] == "lower":
        scaled = 1.0 - scaled
    elif spec["direction"] != "higher":
        raise ValueError(f"Unknown direction for {spec['name']}: {spec['direction']}")
    return float(spec["weight"]) * scaled


def score_record(metrics: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    points: dict[str, float] = {}
    missing: list[str] = []
    section_points: defaultdict[str, float] = defaultdict(float)
    section_available: defaultdict[str, float] = defaultdict(float)
    observed_points = 0.0
    available_weight = 0.0
    total_weight = sum(float(spec["weight"]) for spec in config["metrics"])

    for spec in config["metrics"]:
        name = spec["name"]
        value = metrics.get(name)
        if value is None or (isinstance(value, float) and not math.isfinite(value)):
            missing.append(name)
            continue
        result = metric_points(float(value), spec)
        weight = float(spec["weight"])
        points[name] = result
        observed_points += result
        available_weight += weight
        section_points[spec["section"]] += result
        section_available[spec["section"]] += weight

    completeness = available_weight / total_weight if total_weight else 0.0
    normalized = 100.0 * observed_points / available_weight if available_weight else 0.0
    return {
        "score_version": config["version"],
        "formal_quality_score": observed_points if math.isclose(completeness, 1.0) else None,
        "observed_points": observed_points,
        "available_weight": available_weight,
        "score_completeness": completeness,
        "normalized_observed_score": normalized,
        "metric_points": points,
        "section_points": dict(section_points),
        "section_available_weight": dict(section_available),
        "missing_metrics": missing,
    }


def score_band(score: float, config: dict[str, Any]) -> str:
    bands = config["score_bands"]
    if score >= bands["core"]:
        return "core"
    if score >= bands["strong"]:
        return "strong"
    if score >= bands["qualified"]:
        return "qualified"
    if score >= bands["research"]:
        return "research"
    return "fail"


def main() -> None:
    parser = argparse.ArgumentParser(description="Score one JSON metric record")
    parser.add_argument("metrics_json", help="JSON object or path to a JSON file")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    args = parser.parse_args()
    metrics = load_json_argument(args.metrics_json)
    config = load_config(args.config)
    result = score_record(metrics, config)
    result["provisional_band"] = score_band(result["normalized_observed_score"], config)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
