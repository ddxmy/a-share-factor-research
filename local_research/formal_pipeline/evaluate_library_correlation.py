#!/usr/bin/env python3
"""Measure frozen candidates against active research and legacy libraries."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import pandas as pd

from evaluate_factors import PROJECT_ROOT, FormulaExecutor, load_factor_records, load_panel, preprocess_signal
from screen_discovery import average_abs_daily_spearman_matrix


DISCOVERY_START = pd.Timestamp("2016-01-01")
DISCOVERY_END = pd.Timestamp("2020-12-31")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json_exclusive(path: Path, payload: Any) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def load_library_records(index_path: Path) -> dict[str, dict[str, Any]]:
    index = json.loads(index_path.read_text(encoding="utf-8"))
    selected = {
        "local_research": "active_research",
        "legacy_benchmark": "legacy_benchmark",
    }
    records: dict[str, dict[str, Any]] = {}
    for library_name, role in selected.items():
        specification = index["libraries"][library_name]
        path = (PROJECT_ROOT / specification["path"]).resolve()
        payload = json.loads(path.read_text(encoding="utf-8"))
        if int(specification["factor_count"]) != len(payload.get("factors", [])):
            raise RuntimeError(f"Library count mismatch: {library_name}")
        for record in payload["factors"]:
            factor_id = str(record["factor_id"])
            if factor_id in records:
                raise RuntimeError(f"Duplicate reference-library factor: {factor_id}")
            formula = str(record["formula"])
            formula_hash = hashlib.sha256(formula.encode("utf-8")).hexdigest()
            if record.get("formula_hash") and record["formula_hash"] != formula_hash:
                raise RuntimeError(f"Reference-library formula hash mismatch: {factor_id}")
            records[factor_id] = {
                "factor_id": factor_id,
                "factor_name": record.get("factor_name", factor_id),
                "formula": formula,
                "formula_hash": formula_hash,
                "library_name": library_name,
                "library_role": role,
                "library_path": str(path),
                "library_sha256": sha256_file(path),
            }
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", required=True)
    parser.add_argument("--frozen-manifest", required=True)
    parser.add_argument("--campaign-manifest", required=True)
    parser.add_argument("--script-version", required=True)
    parser.add_argument("--library-index", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    panel_path = Path(args.panel).resolve()
    panel_manifest = json.loads(
        panel_path.with_suffix(".manifest.json").read_text(encoding="utf-8")
    )
    frozen_path = Path(args.frozen_manifest).resolve()
    frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
    campaign_path = Path(args.campaign_manifest).resolve()
    campaign = json.loads(campaign_path.read_text(encoding="utf-8"))
    library_index_path = Path(args.library_index).resolve()
    if frozen.get("status") != "formula_frozen_validation_sealed":
        raise RuntimeError("Formula set is not frozen")
    if campaign.get("campaign_hash") != frozen.get("campaign_hash"):
        raise RuntimeError("Campaign and frozen formula-set hashes differ")
    if panel_manifest.get("research_stage") != "factor_validation":
        raise RuntimeError("Library correlation requires a factor_validation panel")
    if panel_manifest.get("output_sha256") != sha256_file(panel_path):
        raise RuntimeError("Panel hash differs from its manifest")
    for key, expected in {
        "data_snapshot": campaign["data_snapshot"],
        "label_version": campaign["label_version"],
        "universe_sha256": campaign["universe_version"],
    }.items():
        if panel_manifest.get(key) != expected:
            raise RuntimeError(f"Panel identity mismatch: {key}")

    frozen_records = {item["factor_id"]: item for item in frozen["frozen_candidates"]}
    scripts = {
        item["factor_id"]: item
        for item in load_factor_records(PROJECT_ROOT / "factor_script" / args.script_version)
        if item["factor_id"] in frozen_records
    }
    if set(scripts) != set(frozen_records):
        raise RuntimeError("Frozen candidate scripts are missing")
    for factor_id, record in scripts.items():
        if record["formula_hash"] != frozen_records[factor_id]["formula_hash"]:
            raise RuntimeError(f"Frozen candidate formula changed: {factor_id}")
    library_records = load_library_records(library_index_path)
    overlap = set(frozen_records) & set(library_records)
    if overlap:
        raise RuntimeError(f"Frozen candidates already exist in the reference library: {sorted(overlap)}")

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    metadata = load_panel(panel_path)
    dates = metadata.index.get_level_values("dt")
    discovery_metadata = metadata.loc[(dates >= DISCOVERY_START) & (dates <= DISCOVERY_END)]
    executor = FormulaExecutor(str(panel_path), start_date=20150101, end_date=20201231)
    signals: dict[str, pd.Series] = {}
    all_records = [
        *[
            {**scripts[factor_id], "record_role": "frozen_candidate"}
            for factor_id in frozen_records
        ],
        *[
            {**record, "record_role": record["library_role"]}
            for record in library_records.values()
        ],
    ]
    failures: list[dict[str, str]] = []
    for position, record in enumerate(all_records, start=1):
        try:
            prepared = preprocess_signal(executor.compute(record["formula"]), discovery_metadata)
            signals[record["factor_id"]] = prepared["neutral_signal"]
            print(
                f"[{position}/{len(all_records)}] prepared {record['factor_id']} "
                f"({record['record_role']})",
                flush=True,
            )
        except Exception as exc:
            failures.append({"factor_id": record["factor_id"], "error": str(exc)})
    if failures or set(signals) != {record["factor_id"] for record in all_records}:
        raise RuntimeError(f"Library-correlation signal preparation incomplete: {failures}")

    matrix = average_abs_daily_spearman_matrix(signals)
    matrix.to_csv(output_dir / "correlation_matrix.csv")
    pairs = []
    for candidate_id in frozen_records:
        for library_id, library in library_records.items():
            pairs.append(
                {
                    "factor_id": candidate_id,
                    "library_factor_id": library_id,
                    "library_factor_name": library["factor_name"],
                    "library_name": library["library_name"],
                    "library_role": library["library_role"],
                    "average_abs_daily_spearman": float(matrix.loc[candidate_id, library_id]),
                }
            )
    pair_frame = pd.DataFrame(pairs).sort_values(
        ["factor_id", "average_abs_daily_spearman"], ascending=[True, False]
    )
    pair_frame.to_csv(output_dir / "candidate_library_correlations.csv", index=False)

    summaries = []
    for factor_id, group in pair_frame.groupby("factor_id", sort=False):
        best = group.iloc[0]
        active = group.loc[group["library_role"].eq("active_research")]
        legacy = group.loc[group["library_role"].eq("legacy_benchmark")]
        summaries.append(
            {
                "factor_id": factor_id,
                "max_abs_library_correlation": float(best["average_abs_daily_spearman"]),
                "best_library_match": best["library_factor_id"],
                "best_library_role": best["library_role"],
                "max_abs_active_research_correlation": float(
                    active["average_abs_daily_spearman"].max()
                ),
                "max_abs_legacy_benchmark_correlation": float(
                    legacy["average_abs_daily_spearman"].max()
                ),
            }
        )
    pd.DataFrame(summaries).sort_values(
        "max_abs_library_correlation", ascending=False
    ).to_csv(output_dir / "candidate_library_summary.csv", index=False)
    write_json_exclusive(output_dir / "failures.json", [])
    write_json_exclusive(
        output_dir / "run_manifest.json",
        {
            "created_at": pd.Timestamp.now(tz="Asia/Shanghai").isoformat(),
            "stage": "factor_validation_library_correlation",
            "campaign_hash": campaign["campaign_hash"],
            "formula_set_hash": frozen["formula_set_hash"],
            "frozen_manifest": str(frozen_path),
            "frozen_manifest_sha256": sha256_file(frozen_path),
            "library_index": str(library_index_path),
            "library_index_sha256": sha256_file(library_index_path),
            "reference_library_count": len(library_records),
            "candidate_count": len(frozen_records),
            "signal_dates": [str(DISCOVERY_START.date()), str(DISCOVERY_END.date())],
            "correlation_metric": "mean absolute daily cross-sectional Spearman",
            "validation_labels_used": False,
            "validation_labels_opened_elsewhere_in_campaign": True,
            "generation_may_resume": False,
        },
    )
    print(f"Saved library-correlation audit to {output_dir}", flush=True)


if __name__ == "__main__":
    main()
