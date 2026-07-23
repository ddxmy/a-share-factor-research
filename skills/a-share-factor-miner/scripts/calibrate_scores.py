#!/usr/bin/env python3
"""Provisional score calibration from existing local HS300 factor outputs.

This calibration intentionally reports an incomplete score.  The current result set lacks
industry/cap neutralization, parameter perturbations, transfer universes, next-open-to-close
labels, and 20 bps cost stress required by the formal evaluator.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from quality_score import DEFAULT_CONFIG, load_config, score_band, score_record


def newey_west_t(values: pd.Series) -> tuple[float, float, int]:
    x = pd.Series(values, dtype=float).dropna().to_numpy()
    n = len(x)
    if n < 10:
        return float("nan"), float("nan"), 0
    lag = max(1, int(np.floor(4 * (n / 100) ** (2 / 9))))
    centered = x - x.mean()
    long_run_variance = float(np.dot(centered, centered) / n)
    for offset in range(1, min(lag, n - 1) + 1):
        weight = 1.0 - offset / (lag + 1)
        covariance = float(np.dot(centered[offset:], centered[:-offset]) / n)
        long_run_variance += 2.0 * weight * covariance
    if long_run_variance <= 0:
        return float("nan"), float("nan"), lag
    standard_error = np.sqrt(long_run_variance / n)
    t_value = float(x.mean() / standard_error)
    return t_value, float(stats.norm.sf(t_value)), lag


def bh_qvalues(p_values: pd.Series) -> pd.Series:
    valid = p_values.dropna().sort_values()
    if valid.empty:
        return pd.Series(np.nan, index=p_values.index, dtype=float)
    count = len(valid)
    raw = valid.to_numpy() * count / np.arange(1, count + 1)
    adjusted = np.minimum.accumulate(raw[::-1])[::-1]
    result = pd.Series(np.nan, index=p_values.index, dtype=float)
    result.loc[valid.index] = np.clip(adjusted, 0, 1)
    return result


def annualized_sharpe(returns: pd.Series) -> float:
    values = returns.dropna()
    return float(values.mean() / (values.std(ddof=1) + 1e-12) * np.sqrt(252))


def max_drawdown_abs(returns: pd.Series) -> float:
    values = returns.dropna()
    wealth = (1 + values).cumprod()
    return float(abs((wealth / wealth.cummax() - 1).min()))


def halfyear_stats(ic: pd.Series) -> tuple[float, float, int]:
    frame = pd.DataFrame({"ic": ic.dropna()})
    if frame.empty:
        return float("nan"), float("nan"), 0
    labels = frame.index.year.astype(str) + "H" + np.where(frame.index.month <= 6, "1", "2")
    means = frame.groupby(labels)["ic"].mean()
    return float((means > 0).mean()), float(means.min()), len(means)


def quantile_monotonicity(daily: pd.DataFrame, signs: np.ndarray | None = None) -> float:
    group_columns = sorted(
        [column for column in daily.columns if column.startswith("group_") and column.endswith("_return")],
        key=lambda name: int(name.split("_")[1]),
    )
    if len(group_columns) < 2:
        return float("nan")
    values = daily[group_columns].to_numpy(dtype=float)
    if signs is not None:
        reversed_values = values[:, ::-1]
        values = np.where(signs[:, None] >= 0, values, reversed_values)
    means = np.nanmean(values, axis=0)
    return float(stats.spearmanr(np.arange(1, len(means) + 1), means, nan_policy="omit").statistic)


def load_daily(root: Path, factor_id: str, period: str) -> pd.DataFrame:
    path = root / f"factor_{factor_id}_{period}_daily.csv"
    return pd.read_csv(path, parse_dates=["dt"]).set_index("dt").sort_index()


def existing_metric_record(root: Path, audit_row: pd.Series, raw_summary: pd.DataFrame) -> tuple[dict, dict]:
    factor_id = str(audit_row["factor_id"])
    direction = int(audit_row["train_direction"])
    train_daily = load_daily(root, factor_id, "in_sample")
    validation_daily = load_daily(root, factor_id, "out_of_sample")
    train_ic = direction * train_daily["ic"]
    validation_ic = direction * validation_daily["ic"]
    half_ratio, worst_half, half_count = halfyear_stats(validation_ic)
    raw_validation = raw_summary.loc[
        (raw_summary["factor_id"].astype(str) == factor_id)
        & (raw_summary["period"] == "out_of_sample")
    ].iloc[0]
    monotonicity = direction * float(raw_validation["group_return_monotonicity"])
    discovery_ic = float(train_ic.mean())
    validation_mean_ic = float(validation_ic.mean())
    metrics = {
        "discovery_rank_ic": discovery_ic,
        "validation_rank_ic": validation_mean_ic,
        "validation_icir": float(validation_mean_ic / (validation_ic.std(ddof=1) + 1e-12)),
        "ic_retention": float(min(validation_mean_ic / max(discovery_ic, 1e-12), 1.0)),
        "monthly_ic_hit_rate": float((validation_ic.groupby(validation_ic.index.to_period("M")).mean() > 0).mean()),
        "positive_halfyear_ratio": half_ratio,
        "worst_halfyear_ic": worst_half,
        "quantile_monotonicity": monotonicity,
        "net_sharpe_10bps": float(audit_row["validation_oriented_sharpe"]),
        "max_drawdown_abs": abs(float(audit_row["validation_oriented_max_drawdown"])),
        "max_abs_library_correlation": float(audit_row["max_abs_factor_correlation"]),
        "average_daily_turnover": float(audit_row["validation_average_daily_turnover"]),
        "average_signal_coverage": float(audit_row["validation_average_signal_coverage"]),
    }
    t_value, p_value, lag = newey_west_t(validation_ic)
    diagnostics = {
        "factor_id": factor_id,
        "factor_name": audit_row["factor_name"],
        "formula": audit_row["formula"],
        "train_direction": direction,
        "newey_west_t": t_value,
        "one_sided_p": p_value,
        "newey_west_lag": lag,
        "validation_halfyear_count": half_count,
    }
    return metrics, diagnostics


def randomized_control(
    root: Path,
    factor_id: str,
    rng: np.random.Generator,
) -> tuple[dict, dict]:
    train = load_daily(root, factor_id, "in_sample")
    validation = load_daily(root, factor_id, "out_of_sample")
    train_signs = rng.choice(np.array([-1, 1]), size=len(train))
    validation_signs = rng.choice(np.array([-1, 1]), size=len(validation))
    randomized_train_ic = train["ic"].to_numpy(dtype=float) * train_signs
    discovery_direction = 1 if np.nanmean(randomized_train_ic) >= 0 else -1
    train_ic = pd.Series(discovery_direction * randomized_train_ic, index=train.index)
    validation_ic = pd.Series(
        discovery_direction * validation["ic"].to_numpy(dtype=float) * validation_signs,
        index=validation.index,
    )
    validation_effective_signs = discovery_direction * validation_signs
    flips = np.r_[False, validation_effective_signs[1:] != validation_effective_signs[:-1]]
    turnover = validation["turnover"].to_numpy(dtype=float)
    randomized_turnover = np.where(flips, np.maximum(turnover, 2.0), turnover)
    cost = randomized_turnover * 10.0 / 10_000
    gross = discovery_direction * validation_signs * validation["gross_long_short_return"].to_numpy(dtype=float)
    net = pd.Series(gross - cost, index=validation.index)
    half_ratio, worst_half, half_count = halfyear_stats(validation_ic)
    discovery_ic = float(train_ic.mean())
    validation_mean_ic = float(validation_ic.mean())
    metrics = {
        "discovery_rank_ic": discovery_ic,
        "validation_rank_ic": validation_mean_ic,
        "validation_icir": float(validation_mean_ic / (validation_ic.std(ddof=1) + 1e-12)),
        "ic_retention": float(min(validation_mean_ic / max(discovery_ic, 1e-12), 1.0)),
        "monthly_ic_hit_rate": float((validation_ic.groupby(validation_ic.index.to_period("M")).mean() > 0).mean()),
        "positive_halfyear_ratio": half_ratio,
        "worst_halfyear_ic": worst_half,
        "quantile_monotonicity": quantile_monotonicity(validation, validation_effective_signs),
        "net_sharpe_10bps": annualized_sharpe(net),
        "max_drawdown_abs": max_drawdown_abs(net),
        # Give null controls maximum novelty; this is deliberately conservative.
        "max_abs_library_correlation": 0.0,
        "average_daily_turnover": float(np.nanmean(randomized_turnover)),
        "average_signal_coverage": float(validation["signal_coverage"].mean()),
    }
    t_value, p_value, lag = newey_west_t(validation_ic)
    return metrics, {
        "source_factor_id": factor_id,
        "newey_west_t": t_value,
        "one_sided_p": p_value,
        "newey_west_lag": lag,
        "validation_halfyear_count": half_count,
    }


def gate_failures(row: pd.Series, config: dict, require_halfyears: bool) -> list[str]:
    gates = config["hard_gates"]
    failures: list[str] = []
    if row["average_signal_coverage"] < gates["min_coverage"]:
        failures.append("coverage")
    if row["discovery_rank_ic"] < gates["min_discovery_rank_ic"]:
        failures.append("discovery_ic")
    if row["validation_rank_ic"] < gates["min_validation_rank_ic"]:
        failures.append("validation_ic")
    if require_halfyears and row["positive_halfyear_ratio"] < gates["min_positive_halfyear_ratio"]:
        failures.append("halfyear_signs")
    if row["newey_west_t"] < gates["min_newey_west_t"]:
        failures.append("newey_west_t")
    if row["fdr_q"] > gates["max_fdr_q"]:
        failures.append("fdr_q")
    if row["max_abs_library_correlation"] >= gates["hard_duplicate_correlation"]:
        failures.append("hard_duplicate")
    return failures


def finalize_rows(records: list[dict], config: dict, require_halfyears: bool) -> pd.DataFrame:
    frame = pd.DataFrame(records)
    frame["fdr_q"] = bh_qvalues(frame["one_sided_p"])
    failures = []
    for _, row in frame.iterrows():
        failed = gate_failures(row, config, require_halfyears=require_halfyears)
        failures.append(",".join(failed))
    frame["available_gate_failures"] = failures
    frame["passes_available_gates"] = frame["available_gate_failures"].eq("")
    frame["provisional_band"] = frame["normalized_observed_score"].map(lambda x: score_band(x, config))
    return frame


def quantiles(series: pd.Series) -> dict[str, float]:
    return {str(level): float(series.quantile(level)) for level in (0.0, 0.25, 0.5, 0.75, 0.9, 0.95, 1.0)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Calibrate provisional local factor scores")
    parser.add_argument("--results-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--noise-controls", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=20260717)
    args = parser.parse_args()

    root = Path(args.results_dir).resolve()
    output = Path(args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    config = load_config(args.config)
    audit = pd.read_csv(root / "factor_oriented_audit.csv")
    raw_summary = pd.read_csv(root / "factor_summary.csv")

    real_records: list[dict] = []
    metric_cache: dict[str, dict] = {}
    for _, audit_row in audit.iterrows():
        metrics, diagnostics = existing_metric_record(root, audit_row, raw_summary)
        scored = score_record(metrics, config)
        factor_id = str(diagnostics["factor_id"])
        metric_cache[factor_id] = metrics
        real_records.append({
            **diagnostics,
            **metrics,
            **{key: value for key, value in scored.items() if key not in {"metric_points", "section_points", "section_available_weight", "missing_metrics"}},
            "missing_metrics": ",".join(scored["missing_metrics"]),
            "score_components_json": json.dumps(scored["metric_points"], sort_keys=True),
        })

    # The current 2024 validation window contains only one half-year.  Report the
    # half-year metric, but do not pretend the formal 3-of-4 gate is observable.
    real = finalize_rows(real_records, config, require_halfyears=False)
    real.to_csv(output / "existing_factor_scores_provisional.csv", index=False)

    rng = np.random.default_rng(args.seed)
    factor_ids = sorted(metric_cache)
    null_records: list[dict] = []
    for control_id in range(1, args.noise_controls + 1):
        source_id = str(rng.choice(factor_ids))
        metrics, diagnostics = randomized_control(root, source_id, rng)
        scored = score_record(metrics, config)
        null_records.append({
            "control_id": f"null_{control_id:04d}",
            **diagnostics,
            **metrics,
            **{key: value for key, value in scored.items() if key not in {"metric_points", "section_points", "section_available_weight", "missing_metrics"}},
            "missing_metrics": ",".join(scored["missing_metrics"]),
        })
    nulls = finalize_rows(null_records, config, require_halfyears=False)
    nulls.to_csv(output / "sign_randomized_null_scores.csv", index=False)

    bands = config["score_bands"]
    qualified = bands["qualified"]
    core = bands["core"]
    passing_real = real.loc[real["passes_available_gates"]].sort_values(
        "normalized_observed_score", ascending=False
    )
    report = {
        "status": "provisional_close_to_close_non_neutralized",
        "score_version": config["version"],
        "source_results": str(root),
        "existing_factors": len(real),
        "null_controls": len(nulls),
        "formal_score_available": False,
        "median_score_completeness": float(real["score_completeness"].median()),
        "validation_halfyears": int(real["validation_halfyear_count"].max()),
        "existing_score_quantiles": quantiles(real["normalized_observed_score"]),
        "null_score_quantiles": quantiles(nulls["normalized_observed_score"]),
        "existing_available_gate_passes": int(real["passes_available_gates"].sum()),
        "existing_qualified_and_gate_passes": int(
            ((real["normalized_observed_score"] >= qualified) & real["passes_available_gates"]).sum()
        ),
        "null_available_gate_pass_rate": float(nulls["passes_available_gates"].mean()),
        "null_qualified_and_gate_pass_rate": float(
            ((nulls["normalized_observed_score"] >= qualified) & nulls["passes_available_gates"]).mean()
        ),
        "null_qualified_score_only_rate": float(
            (nulls["normalized_observed_score"] >= qualified).mean()
        ),
        "null_core_score_only_rate": float(
            (nulls["normalized_observed_score"] >= core).mean()
        ),
        "provisional_available_gate_candidates": [
            {
                "factor_id": str(row["factor_id"]),
                "normalized_observed_score": float(row["normalized_observed_score"]),
                "validation_rank_ic": float(row["validation_rank_ic"]),
                "newey_west_t": float(row["newey_west_t"]),
                "fdr_q": float(row["fdr_q"]),
            }
            for _, row in passing_real.iterrows()
        ],
        "unavailable_formal_components": [
            "parameter stability",
            "20 bps cost retention",
            "industry/log-cap neutralization retention",
            "CSI 500 transfer",
            "liquid all-A transfer",
            "secondary-label robustness under the formal primary label",
            "four validation half-years",
            "economic audit gate",
        ],
        "calibration_decision": "Keep v1 thresholds provisional and enforce gate-first scoring.",
        "decision_rule": (
            "A factor is ineligible if any hard gate fails; among eligible factors, require "
            "quality score >= 65 and rank by score. Never admit on score alone."
        ),
        "red_sea_update_allowed": False,
        "calibration_rule": "Do not auto-change numeric thresholds from this provisional run.",
    }
    (output / "calibration_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    markdown = f"""# Provisional Quality-Score Calibration

- Status: `{report['status']}`
- Existing valid factors: {report['existing_factors']}
- Sign-randomized empirical null controls: {report['null_controls']}
- Median score completeness: {report['median_score_completeness']:.1%}
- Available-gate passes among existing factors: {report['existing_available_gate_passes']}
- Qualified-score plus available-gate passes: {report['existing_qualified_and_gate_passes']}
- Null available-gate pass rate: {report['null_available_gate_pass_rate']:.2%}
- Null qualified-score plus gate pass rate: {report['null_qualified_and_gate_pass_rate']:.2%}
- Null score-only rate at qualified (>=65): {report['null_qualified_score_only_rate']:.2%}
- Null score-only rate at core (>=85): {report['null_core_score_only_rate']:.2%}

Calibration decision: **gate first, score second**. A failed hard gate makes a factor
ineligible regardless of its score. Among eligible factors, require score >=65 and use the
score for ranking. The score-only null rates above show why this ordering is mandatory.

This run is a threshold-distribution diagnostic, not a formal factor admission. It uses the
existing close-to-close, non-neutralized 2022-2024 output and only one validation half-year.
Do not update the production library or Red Sea memory from these scores.
"""
    (output / "calibration_report.md").write_text(markdown, encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"Saved provisional calibration to {output}")


if __name__ == "__main__":
    main()
