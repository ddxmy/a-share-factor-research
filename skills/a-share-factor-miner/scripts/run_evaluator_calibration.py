#!/usr/bin/env python3
"""Calibrate and, only on explicit acceptance, freeze the local factor evaluator.

Calibration controls are isolated from candidate-history FDR and active libraries.
The script never reads synthesis-validation (2023-2024) or lockbox (2025+) labels.
"""

from __future__ import annotations

import argparse
import ast
import gc
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
FORMAL_PIPELINE = PROJECT_ROOT / "local_research" / "formal_pipeline"
EVALUATION_PACKAGE = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(FORMAL_PIPELINE))
sys.path.insert(0, str(EVALUATION_PACKAGE))

from evaluate_factors import (  # noqa: E402
    FormulaExecutor,
    daily_ic,
    evaluate_record,
    hard_gate_failures,
    load_panel,
    preprocess_signal,
)
from calibrate_scores import bh_qvalues  # noqa: E402
from quality_score import DEFAULT_CONFIG, load_config, score_band, score_record  # noqa: E402
from evaluation import evaluator as evaluator_module  # noqa: E402


DEFAULT_CONTROLS = PROJECT_ROOT / "skills" / "a-share-factor-miner" / "references" / "calibration_controls_v1.json"
DISCOVERY_START = pd.Timestamp("2016-01-01")
DISCOVERY_END = pd.Timestamp("2020-12-31")
VALIDATION_START = pd.Timestamp("2021-01-01")
VALIDATION_END = pd.Timestamp("2022-12-31")
FORBIDDEN_NAMES = {
    "next_open_to_close",
    "next_close_to_close",
    "primary_label_available",
    "execution_date",
    "future_return",
    "label",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def preflight_formula(formula: str, executor: FormulaExecutor) -> list[str]:
    failures: list[str] = []
    try:
        tree = ast.parse(formula, mode="eval")
    except SyntaxError:
        return ["syntax_error"]
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    if names & FORBIDDEN_NAMES:
        failures.append("future_or_label_field")
    unknown = names - set(executor.namespace)
    if unknown:
        failures.append("unknown_or_unavailable_field:" + ",".join(sorted(unknown)))
    return failures


def deterministic_noise(executor: FormulaExecutor, seed: int, control_id: str) -> pd.DataFrame:
    dates = executor.md["index"]
    tickers = executor.md["columns"]
    date_codes = pd.util.hash_array(dates.to_numpy(), categorize=False).astype("uint64")
    ticker_codes = pd.util.hash_array(tickers.to_numpy(dtype=object), categorize=False).astype("uint64")
    salt = int.from_bytes(hashlib.sha256(f"{seed}|{control_id}".encode()).digest()[:8], "little")
    mixed = (
        date_codes[:, None] * np.uint64(0x9E3779B185EBCA87)
        ^ ticker_codes[None, :] * np.uint64(0xC2B2AE3D27D4EB4F)
        ^ np.uint64(salt)
    )
    # Convert the high 53 bits to an approximately uniform score in (0, 1).
    values = ((mixed >> np.uint64(11)).astype("float64") + 0.5) / float(2**53)
    return pd.DataFrame(values, index=dates, columns=tickers)


class ControlExecutor:
    def __init__(self, base: FormulaExecutor, signals: dict[str, pd.DataFrame] | None = None):
        self.base = base
        self.signals = signals or {}

    def compute(self, formula: str) -> pd.DataFrame:
        if formula in self.signals:
            return self.signals[formula]
        return self.base.compute(formula)


def oriented_transfer_ic(
    formula: str,
    direction: int,
    executor: ControlExecutor,
    metadata: pd.DataFrame,
) -> float:
    prepared = preprocess_signal(executor.compute(formula), metadata)
    evaluable = prepared.loc[prepared["primary_evaluable"]]
    dates = evaluable.index.get_level_values("dt")
    validation = evaluable.loc[(dates >= VALIDATION_START) & (dates <= VALIDATION_END)]
    return float(direction * daily_ic(validation, "neutral_signal", "next_open_to_close").mean())


def parameter_stability(
    control: dict[str, Any],
    direction: int,
    base_validation_ic: float,
    executor: ControlExecutor,
    metadata: pd.DataFrame,
) -> float:
    if control.get("parameter_free"):
        return 1.0
    variants = control.get("formula_variants", [])
    if not variants:
        return float("nan")
    dates = metadata.index.get_level_values("dt")
    validation_metadata = metadata.loc[(dates >= VALIDATION_START) & (dates <= VALIDATION_END)]
    stable = 0
    for variant in variants:
        prepared = preprocess_signal(executor.compute(variant["formula"]), validation_metadata)
        evaluable = prepared.loc[prepared["primary_evaluable"]]
        variant_ic = float(
            direction * daily_ic(evaluable, "neutral_signal", "next_open_to_close").mean()
        )
        retention = variant_ic / base_validation_ic if base_validation_ic > 0 else float("nan")
        stable += int(variant_ic > 0 and retention >= 0.50)
    return stable / len(variants)


def discovery_signal(
    formula: str,
    executor: ControlExecutor,
    metadata: pd.DataFrame,
) -> pd.Series:
    prepared = preprocess_signal(executor.compute(formula), metadata)
    dates = prepared.index.get_level_values("dt")
    return prepared.loc[
        (dates >= DISCOVERY_START) & (dates <= DISCOVERY_END), "neutral_signal"
    ]


def mean_daily_cross_sectional_correlation(left: pd.Series, right: pd.Series) -> float:
    joined = pd.concat([left.rename("left"), right.rename("right")], axis=1).dropna()
    if joined.empty:
        return float("nan")

    def correlate(day: pd.DataFrame) -> float:
        if len(day) < 30 or day["left"].nunique() < 2 or day["right"].nunique() < 2:
            return float("nan")
        return float(day["left"].corr(day["right"], method="spearman"))

    return float(joined.groupby(level="dt", sort=False).apply(correlate).mean())


def pairwise_daily_signal_correlations(signals: dict[str, pd.Series]) -> pd.DataFrame:
    """Mean daily Spearman matrix, ranking all controls once per date."""
    matrix = pd.concat(signals, axis=1)
    columns = matrix.columns
    sums = np.zeros((len(columns), len(columns)), dtype=float)
    counts = np.zeros((len(columns), len(columns)), dtype=np.int64)
    for _, day in matrix.groupby(level="dt", sort=False):
        correlation = day.corr(method="spearman", min_periods=30).to_numpy(dtype=float)
        valid = np.isfinite(correlation)
        sums[valid] += correlation[valid]
        counts[valid] += 1
    values = np.divide(sums, counts, out=np.full_like(sums, np.nan), where=counts > 0)
    return pd.DataFrame(values, index=columns, columns=columns)


def write_checkpoint(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=True,
            default=lambda value: value.item() if hasattr(value, "item") else str(value),
        ),
        encoding="utf-8",
    )


def clear_executor(executor: FormulaExecutor | None) -> None:
    if executor is not None:
        del executor
    evaluator_module._MD_CACHE.clear()
    gc.collect()


def panel_manifest(path: Path) -> dict[str, Any]:
    manifest_path = path.with_suffix(".manifest.json")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if payload.get("research_stage") != "factor_validation":
        raise RuntimeError(f"Calibration requires factor_validation panel: {path}")
    end = pd.Timestamp(payload["range"][1])
    if end > VALIDATION_END:
        raise RuntimeError(f"Calibration panel reads beyond 2022-12-31: {path}")
    return payload


def add_full_score(row: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    scored = score_record(row, config)
    failures = hard_gate_failures(pd.Series(row), config)
    corr = row.get("max_abs_library_correlation")
    if corr is None or not math.isfinite(float(corr)):
        failures.append("library_correlation_missing")
    elif float(corr) >= config["hard_gates"]["hard_duplicate_correlation"]:
        failures.append("hard_duplicate")
    return {
        **row,
        "hard_gate_failures": ",".join(dict.fromkeys(failures)),
        "passes_available_hard_gates": not failures,
        "score_version": scored["score_version"],
        "formal_quality_score": scored["formal_quality_score"],
        "observed_points": scored["observed_points"],
        "available_weight": scored["available_weight"],
        "normalized_observed_score": scored["normalized_observed_score"],
        "score_completeness": scored["score_completeness"],
        "missing_metrics": ",".join(scored["missing_metrics"]),
        "score_components_json": json.dumps(scored["metric_points"], sort_keys=True),
        "score_band": score_band(scored["normalized_observed_score"], config),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hs300-panel", required=True)
    parser.add_argument("--csi500-panel", required=True)
    parser.add_argument("--liquid-all-a-panel", required=True)
    parser.add_argument("--controls", default=str(DEFAULT_CONTROLS))
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--noise-count", type=int)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    if output_dir.exists() and any(output_dir.iterdir()) and not args.resume:
        raise FileExistsError(f"Non-empty output directory requires --resume: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    controls_path = Path(args.controls).resolve()
    config_path = Path(args.config).resolve()
    controls = json.loads(controls_path.read_text(encoding="utf-8"))
    config = load_config(config_path)
    formula_controls = controls["formula_controls"]
    noise_count = args.noise_count if args.noise_count is not None else int(controls["noise"]["count"])
    if noise_count <= 0:
        raise ValueError("noise-count must be positive")

    paths = {
        "hs300": Path(args.hs300_panel).resolve(),
        "csi500": Path(args.csi500_panel).resolve(),
        "liquid_all_a": Path(args.liquid_all_a_panel).resolve(),
    }
    manifests = {name: panel_manifest(path) for name, path in paths.items()}
    snapshots = {manifest["data_snapshot"] for manifest in manifests.values()}
    labels = {manifest["label_version"] for manifest in manifests.values()}
    if len(snapshots) != 1 or len(labels) != 1:
        raise RuntimeError("Calibration panels must bind the same data snapshot and label version")

    rows: list[dict[str, Any]] = []
    signals: dict[str, pd.Series] = {}
    invalid_rows: list[dict[str, Any]] = []
    primary_failures: list[dict[str, str]] = []
    all_primary_controls = list(formula_controls) + [
        {
            "control_id": f"noise_{position:03d}",
            "library": "deterministic_noise",
            "family": "noise",
            "name": f"Deterministic noise {position:03d}",
            "formula": f"__noise_{position:03d}__",
            "economic_hypothesis": "None; negative calibration control.",
            "parameter_free": True,
        }
        for position in range(1, noise_count + 1)
    ]
    primary_checkpoint = output_dir / "primary_checkpoint.json"
    signal_checkpoint = output_dir / "discovery_signal_checkpoint.parquet"
    correlation_checkpoint = output_dir / "correlation_checkpoint.json"
    invalid_checkpoint = output_dir / "invalid_checkpoint.json"
    failure_checkpoint = output_dir / "failure_checkpoint.json"
    if args.resume and correlation_checkpoint.exists():
        rows = json.loads(correlation_checkpoint.read_text(encoding="utf-8"))
        invalid_rows = json.loads(invalid_checkpoint.read_text(encoding="utf-8"))
        primary_failures = json.loads(failure_checkpoint.read_text(encoding="utf-8"))
        print(f"[resume] loaded correlation checkpoint with {len(rows)} controls", flush=True)
    else:
        if args.resume and primary_checkpoint.exists() and signal_checkpoint.exists():
            rows = json.loads(primary_checkpoint.read_text(encoding="utf-8"))
            invalid_rows = json.loads(invalid_checkpoint.read_text(encoding="utf-8"))
            primary_failures = json.loads(failure_checkpoint.read_text(encoding="utf-8"))
            signal_frame = pd.read_parquet(signal_checkpoint)
            signals = {column: signal_frame[column].dropna() for column in signal_frame.columns}
            print(f"[resume] loaded primary checkpoint with {len(rows)} controls", flush=True)
        else:
            primary_metadata = load_panel(paths["hs300"])
            base = FormulaExecutor(str(paths["hs300"]), start_date=20150101, end_date=20221231)
            executor = ControlExecutor(base)
            for control in controls["invalid_controls"]:
                failures = preflight_formula(control["formula"], base)
                if not failures:
                    try:
                        signal = base.compute(control["formula"])
                        unique = signal.nunique(axis=1).median()
                        if not math.isfinite(float(unique)) or unique < 30:
                            failures.append("insufficient_cross_sectional_uniqueness")
                    except Exception as exc:
                        failures.append(type(exc).__name__)
                invalid_rows.append(
                    {**control, "rejected": bool(failures), "rejection_reasons": ",".join(failures)}
                )
            for position, control in enumerate(all_primary_controls, start=1):
                formula = control["formula"]
                try:
                    preflight = [] if control["library"] == "deterministic_noise" else preflight_formula(formula, base)
                    if preflight:
                        raise RuntimeError(";".join(preflight))
                    signal_map = {}
                    if control["library"] == "deterministic_noise":
                        signal_map[formula] = deterministic_noise(base, int(controls["noise"]["seed"]), control["control_id"])
                    local_executor = ControlExecutor(base, signal_map)
                    record = {
                        "factor_id": control["control_id"],
                        "factor_name": control["name"],
                        "formula": formula,
                        "formula_hash": hashlib.sha256(formula.encode()).hexdigest(),
                        "script_path": str(controls_path),
                    }
                    result, _ = evaluate_record(record, local_executor, primary_metadata)
                    result.update(
                        {
                            "control_id": control["control_id"],
                            "control_library": control["library"],
                            "economic_family": control["family"],
                            "economic_hypothesis": control["economic_hypothesis"],
                        }
                    )
                    result["parameter_stability"] = parameter_stability(
                        control,
                        int(result["train_direction"]),
                        float(result["validation_rank_ic"]),
                        local_executor,
                        primary_metadata,
                    )
                    rows.append(result)
                    signals[control["control_id"]] = discovery_signal(formula, local_executor, primary_metadata)
                    print(
                        f"[primary {position}/{len(all_primary_controls)}] {control['control_id']}: "
                        f"IC={result['validation_rank_ic']:.4f}",
                        flush=True,
                    )
                    del signal_map
                    gc.collect()
                except Exception as exc:
                    primary_failures.append({"control_id": control["control_id"], "error": str(exc)})
                    print(f"[primary {position}/{len(all_primary_controls)}] {control['control_id']}: FAILED {exc}", flush=True)
            del executor
            if "local_executor" in locals():
                del local_executor
            clear_executor(base)
            del primary_metadata
            write_checkpoint(primary_checkpoint, rows)
            write_checkpoint(invalid_checkpoint, invalid_rows)
            write_checkpoint(failure_checkpoint, primary_failures)
            pd.concat(signals, axis=1).to_parquet(signal_checkpoint)

        row_map = {row["control_id"]: row for row in rows}
        anchor_ids = [control["control_id"] for control in formula_controls if control["control_id"] in signals]
        correlation_matrix = pairwise_daily_signal_correlations(signals)
        for control_id in signals:
            correlations = correlation_matrix.loc[control_id, anchor_ids].drop(labels=[control_id], errors="ignore")
            row_map[control_id]["max_abs_library_correlation"] = float(correlations.abs().max())
        rows = list(row_map.values())
        write_checkpoint(correlation_checkpoint, rows)
        del signals, correlation_matrix
        gc.collect()

    for universe_name, metric_name in (
        ("csi500", "csi500_rank_ic"),
        ("liquid_all_a", "liquid_all_a_rank_ic"),
    ):
        transfer_checkpoint = output_dir / f"{universe_name}_checkpoint.json"
        if args.resume and transfer_checkpoint.exists():
            rows = json.loads(transfer_checkpoint.read_text(encoding="utf-8"))
            print(f"[resume] loaded {universe_name} checkpoint", flush=True)
            continue
        metadata = load_panel(paths[universe_name])
        base = FormulaExecutor(str(paths[universe_name]), start_date=20150101, end_date=20221231)
        for position, row in enumerate(rows, start=1):
            control_id = row["control_id"]
            formula = row["formula"]
            signal_map = {}
            if row["control_library"] == "deterministic_noise":
                signal_map[formula] = deterministic_noise(base, int(controls["noise"]["seed"]), control_id)
            local_executor = ControlExecutor(base, signal_map)
            try:
                row[metric_name] = oriented_transfer_ic(
                    formula,
                    int(row["train_direction"]),
                    local_executor,
                    metadata,
                )
                print(
                    f"[{universe_name} {position}/{len(rows)}] {control_id}: "
                    f"IC={row[metric_name]:.4f}",
                    flush=True,
                )
            except Exception as exc:
                row[metric_name] = float("nan")
                primary_failures.append(
                    {"control_id": control_id, "stage": universe_name, "error": str(exc)}
                )
        if "local_executor" in locals():
            del local_executor
        clear_executor(base)
        del metadata
        write_checkpoint(transfer_checkpoint, rows)

    frame = pd.DataFrame(rows)
    frame["fdr_q"] = bh_qvalues(frame["one_sided_p"])
    scored = pd.DataFrame([add_full_score(row, config) for row in frame.to_dict("records")])
    scored.to_csv(output_dir / "calibration_control_scores.csv", index=False)
    invalid_frame = pd.DataFrame(invalid_rows)
    invalid_frame.to_csv(output_dir / "invalid_control_audit.csv", index=False)
    (output_dir / "failures.json").write_text(
        json.dumps(primary_failures, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    formula_frame = scored.loc[scored["control_library"].ne("deterministic_noise")]
    noise_frame = scored.loc[scored["control_library"].eq("deterministic_noise")]
    acceptance = controls["acceptance"]
    formula_completion_rate = len(formula_frame) / len(formula_controls)
    formula_completeness = float(formula_frame["score_completeness"].median()) if len(formula_frame) else 0.0
    formula_gate_passes = int(formula_frame["passes_available_hard_gates"].sum())
    noise_gate_rate = float(noise_frame["passes_available_hard_gates"].mean()) if len(noise_frame) else 1.0
    qualified = float(config["score_bands"]["qualified"])
    noise_qualified_gate_rate = float(
        (noise_frame["passes_available_hard_gates"] & noise_frame["normalized_observed_score"].ge(qualified)).mean()
    ) if len(noise_frame) else 1.0
    invalid_rejection_rate = float(invalid_frame["rejected"].mean())
    future_leak_admissions = int(
        invalid_frame.loc[invalid_frame["kind"].eq("future_label"), "rejected"].eq(False).sum()
    )
    checks = {
        "formula_completion_rate": formula_completion_rate >= acceptance["minimum_formula_completion_rate"],
        "formula_score_completeness": formula_completeness >= acceptance["minimum_formula_score_completeness"],
        "formula_available_gate_passes": formula_gate_passes >= acceptance["minimum_formula_available_gate_passes"],
        "noise_available_gate_pass_rate": noise_gate_rate <= acceptance["maximum_noise_available_gate_pass_rate"],
        "noise_qualified_and_gate_pass_rate": noise_qualified_gate_rate <= acceptance["maximum_noise_qualified_and_gate_pass_rate"],
        "invalid_rejection_rate": invalid_rejection_rate >= acceptance["required_invalid_rejection_rate"],
        "future_leak_admissions": future_leak_admissions == acceptance["required_future_leak_admissions"],
        "same_data_snapshot": len(snapshots) == 1,
        "same_label_version": len(labels) == 1,
    }
    passed = all(checks.values())
    report = {
        "status": "pass_evaluator_may_be_frozen" if passed else "fail_keep_evaluator_provisional",
        "evaluator_version": config["version"],
        "controls_version": controls["version"],
        "created_at": pd.Timestamp.now(tz="Asia/Shanghai").isoformat(),
        "candidate_history_fdr_contaminated": False,
        "synthesis_validation_opened": False,
        "lockbox_opened": False,
        "data_snapshot": next(iter(snapshots)),
        "label_version": next(iter(labels)),
        "panels": {
            name: {
                "path": str(paths[name]),
                "sha256": manifests[name]["output_sha256"],
                "universe": manifests[name]["universe_code"],
            }
            for name in paths
        },
        "config_path": str(config_path),
        "config_sha256": sha256_file(config_path),
        "controls_path": str(controls_path),
        "controls_sha256": sha256_file(controls_path),
        "formula_controls_declared": len(formula_controls),
        "formula_controls_completed": len(formula_frame),
        "noise_controls_completed": len(noise_frame),
        "invalid_controls": len(invalid_frame),
        "formula_completion_rate": formula_completion_rate,
        "median_formula_score_completeness": formula_completeness,
        "formula_available_gate_passes": formula_gate_passes,
        "noise_available_gate_pass_rate": noise_gate_rate,
        "noise_qualified_and_gate_pass_rate": noise_qualified_gate_rate,
        "invalid_rejection_rate": invalid_rejection_rate,
        "future_leak_admissions": future_leak_admissions,
        "checks": checks,
        "failed_control_evaluations": len(primary_failures),
        "freeze_decision": passed,
    }
    (output_dir / "calibration_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    markdown = [
        "# Evaluator calibration v1",
        "",
        f"- Decision: **{'PASS / may freeze' if passed else 'FAIL / remain provisional'}**",
        f"- Formula controls completed: {len(formula_frame)}/{len(formula_controls)}",
        f"- Median formula score completeness: {formula_completeness:.1%}",
        f"- Formula controls passing all gates: {formula_gate_passes}",
        f"- Noise all-gate pass rate: {noise_gate_rate:.2%}",
        f"- Noise qualified-and-gate pass rate: {noise_qualified_gate_rate:.2%}",
        f"- Invalid-control rejection rate: {invalid_rejection_rate:.2%}",
        f"- Candidate FDR contaminated: no",
        f"- Synthesis validation / lockbox opened: no / no",
        "",
        "The representative Alpha158 controls are calibration anchors only; the later headline comparison must still build and evaluate the full Alpha158 library.",
    ]
    (output_dir / "calibration_report.md").write_text("\n".join(markdown) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
