#!/usr/bin/env python3
"""Evaluate active factor formulas on the frozen HS300 discovery/validation panel."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EVALUATION_DIR = PROJECT_ROOT / "scripts" / "evaluation"
SKILL_SCRIPTS = PROJECT_ROOT / "skills" / "a-share-factor-miner" / "scripts"
sys.path.insert(0, str(EVALUATION_DIR.parent))
sys.path.insert(0, str(SKILL_SCRIPTS))

from evaluation.evaluator import FormulaExecutor  # noqa: E402
from calibrate_scores import bh_qvalues, newey_west_t  # noqa: E402
from quality_score import load_config, score_band, score_record  # noqa: E402


DISCOVERY_START = pd.Timestamp("2016-01-01")
DISCOVERY_END = pd.Timestamp("2020-12-31")
VALIDATION_START = pd.Timestamp("2021-01-01")
VALIDATION_END = pd.Timestamp("2022-12-31")


def load_factor_records(script_dir: Path) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for path in sorted(script_dir.rglob("*.py")):
        if "_retired" in path.parts:
            continue
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
            constants[node.targets[0].id] = str(ast.literal_eval(node.value))
        if {"FACTOR_NAME", "FORMULA"}.issubset(constants):
            formula = constants["FORMULA"]
            records.append(
                {
                    "factor_id": path.stem,
                    "factor_name": constants["FACTOR_NAME"],
                    "formula": formula,
                    "formula_hash": hashlib.sha256(formula.encode("utf-8")).hexdigest(),
                    "script_path": str(path.relative_to(PROJECT_ROOT)),
                }
            )
    return records


def load_registry_factor_ids(path: Path) -> set[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    factors = payload.get("factors")
    if not isinstance(factors, list):
        raise ValueError(f"Registry must contain a factors list: {path}")
    factor_ids = {
        str(record["factor_id"])
        for record in factors
        if isinstance(record, dict) and "factor_id" in record
    }
    if not factor_ids:
        raise ValueError(f"Registry contains no factor IDs: {path}")
    return factor_ids


def load_panel(path: Path) -> pd.DataFrame:
    columns = [
        "dt",
        "Ticker",
        "float_mkt_cap",
        "l1_code",
        "is_st",
        "can_buy_open",
        "can_sell_open",
        "next_open_to_close",
        "next_close_to_close",
        "primary_label_available",
    ]
    panel = pd.read_parquet(path, columns=columns)
    panel["dt"] = pd.to_datetime(panel["dt"])
    panel["Ticker"] = panel["Ticker"].astype(str)
    panel["log_float_mkt_cap"] = np.log(
        pd.to_numeric(panel["float_mkt_cap"], errors="coerce").where(lambda values: values > 0)
    )
    panel["signal_eligible"] = (
        ~panel["is_st"].fillna(True)
        & panel["l1_code"].notna()
        & panel["log_float_mkt_cap"].notna()
    )
    panel["primary_evaluable"] = (
        panel["signal_eligible"]
        & panel["primary_label_available"].fillna(False)
        & panel["next_open_to_close"].notna()
    )
    return panel.set_index(["dt", "Ticker"]).sort_index()


def neutralize_one_day(day: pd.DataFrame) -> pd.Series:
    usable = day.dropna(subset=["raw_signal", "l1_code", "log_float_mkt_cap"]).copy()
    result = pd.Series(np.nan, index=day.index, dtype=float)
    if len(usable) < 50 or usable["raw_signal"].nunique() < 30:
        return result

    lower, upper = usable["raw_signal"].quantile([0.01, 0.99])
    y = usable["raw_signal"].clip(lower=lower, upper=upper)
    industry_mean_y = y.groupby(usable["l1_code"]).transform("mean")
    size = usable["log_float_mkt_cap"]
    industry_mean_size = size.groupby(usable["l1_code"]).transform("mean")
    within_y = y - industry_mean_y
    within_size = size - industry_mean_size
    denominator = float(np.dot(within_size, within_size))
    gamma = float(np.dot(within_size, within_y) / denominator) if denominator > 1e-12 else 0.0
    residual = within_y - gamma * within_size
    standard_deviation = float(residual.std(ddof=1))
    if not math.isfinite(standard_deviation) or standard_deviation <= 1e-12:
        return result
    result.loc[usable.index] = (residual - residual.mean()) / standard_deviation
    return result


def preprocess_signal(signal: pd.DataFrame, metadata: pd.DataFrame) -> pd.DataFrame:
    raw = signal.stack(future_stack=True).rename("raw_signal")
    raw.index.names = ["dt", "Ticker"]
    joined = metadata.join(raw, how="left")
    joined.loc[~joined["signal_eligible"], "raw_signal"] = np.nan
    neutralized = joined.groupby(level="dt", group_keys=False).apply(
        neutralize_one_day,
        include_groups=False,
    )
    joined["neutral_signal"] = neutralized.reindex(joined.index)
    return joined


def daily_ic(frame: pd.DataFrame, signal_column: str, label_column: str) -> pd.Series:
    def correlation(day: pd.DataFrame) -> float:
        usable = day[[signal_column, label_column]].dropna()
        if len(usable) < 30 or usable[signal_column].nunique() < 2:
            return float("nan")
        return float(usable[signal_column].corr(usable[label_column], method="spearman"))

    return frame.groupby(level="dt", sort=True).apply(correlation).dropna()


def halfyear_statistics(values: pd.Series) -> tuple[float, float, int]:
    if values.empty:
        return float("nan"), float("nan"), 0
    labels = values.index.year.astype(str) + "H" + np.where(values.index.month <= 6, "1", "2")
    means = values.groupby(labels).mean()
    return float(means.gt(0).mean()), float(means.min()), int(len(means))


def annualized_sharpe(values: pd.Series) -> float:
    values = values.dropna()
    if len(values) < 2:
        return float("nan")
    return float(values.mean() / (values.std(ddof=1) + 1e-12) * np.sqrt(252))


def max_drawdown_abs(values: pd.Series) -> float:
    wealth = (1.0 + values.dropna()).cumprod()
    if wealth.empty:
        return float("nan")
    return float(abs((wealth / wealth.cummax() - 1.0).min()))


def portfolio_diagnostics(
    frame: pd.DataFrame,
    direction: int,
    quantiles: int = 5,
) -> tuple[dict[str, float], pd.DataFrame]:
    returns: dict[pd.Timestamp, float] = {}
    group_returns: dict[pd.Timestamp, list[float]] = {}
    weights: dict[pd.Timestamp, pd.Series] = {}
    for date, day in frame.groupby(level="dt", sort=True):
        usable = day[["neutral_signal", "next_open_to_close"]].dropna().copy()
        if len(usable) < 50 or usable["neutral_signal"].nunique() < quantiles:
            continue
        oriented = direction * usable["neutral_signal"]
        try:
            buckets = pd.qcut(oriented, quantiles, labels=False, duplicates="drop")
        except ValueError:
            continue
        if buckets.nunique() != quantiles:
            continue
        group_returns[date] = [
            float(usable.loc[buckets.eq(group), "next_open_to_close"].mean())
            for group in range(quantiles)
        ]
        long_names = buckets.index[buckets.eq(quantiles - 1)].get_level_values("Ticker")
        short_names = buckets.index[buckets.eq(0)].get_level_values("Ticker")
        weight = pd.Series(0.0, index=usable.index.get_level_values("Ticker").unique())
        weight.loc[long_names] = 1.0 / len(long_names)
        weight.loc[short_names] = -1.0 / len(short_names)
        realized = usable.reset_index(level="dt", drop=True)["next_open_to_close"]
        weights[date] = weight
        returns[date] = float((weight * realized.reindex(weight.index)).sum())

    gross = pd.Series(returns, dtype=float).sort_index()
    turnover = pd.Series(index=gross.index, dtype=float)
    previous = pd.Series(dtype=float)
    for date in gross.index:
        current = weights[date]
        names = previous.index.union(current.index)
        turnover.loc[date] = float(
            (
                current.reindex(names, fill_value=0.0)
                - previous.reindex(names, fill_value=0.0)
            ).abs().sum()
            / 2.0
        )
        previous = current
    net_10 = gross - turnover * 10.0 / 10_000.0
    net_20 = gross - turnover * 20.0 / 10_000.0
    grouped = pd.DataFrame.from_dict(group_returns, orient="index").sort_index()
    grouped.columns = [f"group_{position + 1}_return" for position in range(quantiles)]
    means = grouped.mean()
    monotonicity = float(stats.spearmanr(np.arange(1, quantiles + 1), means).statistic)
    gross_mean = float(gross.mean())
    cost_retention = float(net_20.mean() / gross_mean) if gross_mean > 1e-12 else float("nan")
    metrics = {
        "quantile_monotonicity": monotonicity,
        "net_sharpe_10bps": annualized_sharpe(net_10),
        "cost_retention_20bps": cost_retention,
        "max_drawdown_abs": max_drawdown_abs(net_10),
        "average_daily_turnover": float(turnover.mean()),
        "gross_annualized_sharpe": annualized_sharpe(gross),
        "net_20bps_annualized_sharpe": annualized_sharpe(net_20),
    }
    daily = pd.DataFrame(
        {
            "gross_long_short_return": gross,
            "turnover": turnover,
            "net_return_10bps": net_10,
            "net_return_20bps": net_20,
        }
    ).join(grouped, how="left")
    return metrics, daily


def evaluate_record(
    record: dict[str, str],
    executor: FormulaExecutor,
    metadata: pd.DataFrame,
) -> tuple[dict[str, Any], pd.DataFrame]:
    signal = executor.compute(record["formula"])
    prepared = preprocess_signal(signal, metadata)
    evaluable = prepared.loc[prepared["primary_evaluable"]].copy()
    discovery = evaluable.loc[
        (evaluable.index.get_level_values("dt") >= DISCOVERY_START)
        & (evaluable.index.get_level_values("dt") <= DISCOVERY_END)
    ]
    validation = evaluable.loc[
        (evaluable.index.get_level_values("dt") >= VALIDATION_START)
        & (evaluable.index.get_level_values("dt") <= VALIDATION_END)
    ]
    discovery_neutral_ic = daily_ic(discovery, "neutral_signal", "next_open_to_close")
    validation_neutral_ic = daily_ic(validation, "neutral_signal", "next_open_to_close")
    discovery_raw_ic = daily_ic(discovery, "raw_signal", "next_open_to_close")
    validation_raw_ic = daily_ic(validation, "raw_signal", "next_open_to_close")
    validation_secondary_ic = daily_ic(validation, "neutral_signal", "next_close_to_close")
    if discovery_neutral_ic.empty or validation_neutral_ic.empty:
        raise RuntimeError("No usable discovery or validation IC series")
    direction = 1 if discovery_neutral_ic.mean() >= 0 else -1
    discovery_oriented = direction * discovery_neutral_ic
    validation_oriented = direction * validation_neutral_ic
    raw_validation_oriented = direction * validation_raw_ic
    secondary_oriented = direction * validation_secondary_ic
    half_ratio, worst_half, half_count = halfyear_statistics(validation_oriented)
    nw_t, one_sided_p, nw_lag = newey_west_t(validation_oriented)
    portfolio_metrics, portfolio_daily = portfolio_diagnostics(validation, direction)

    eligible_counts = metadata.loc[metadata["primary_evaluable"]].groupby(level="dt").size()
    factor_counts = prepared.loc[
        prepared["primary_evaluable"] & prepared["neutral_signal"].notna()
    ].groupby(level="dt").size()
    coverage = factor_counts / eligible_counts.reindex(factor_counts.index)
    daily_unique = prepared["neutral_signal"].groupby(level="dt").nunique()
    usable_dates = factor_counts.ge(50)
    raw_abs = abs(float(raw_validation_oriented.mean()))
    neutral_abs = abs(float(validation_oriented.mean()))
    metrics: dict[str, Any] = {
        "discovery_rank_ic": float(discovery_oriented.mean()),
        "validation_rank_ic": float(validation_oriented.mean()),
        "validation_icir": float(
            validation_oriented.mean() / (validation_oriented.std(ddof=1) + 1e-12)
        ),
        "annualized_validation_icir": float(
            validation_oriented.mean()
            / (validation_oriented.std(ddof=1) + 1e-12)
            * np.sqrt(252)
        ),
        "ic_retention": float(
            min(validation_oriented.mean() / max(discovery_oriented.mean(), 1e-12), 1.0)
        ),
        "monthly_ic_hit_rate": float(
            validation_oriented.groupby(validation_oriented.index.to_period("M")).mean().gt(0).mean()
        ),
        "positive_halfyear_ratio": half_ratio,
        "worst_halfyear_ic": worst_half,
        "neutralization_retention": neutral_abs / raw_abs if raw_abs > 1e-12 else float("nan"),
        "secondary_label_rank_ic": float(secondary_oriented.mean()),
        "average_signal_coverage": float(coverage.mean()),
        **portfolio_metrics,
    }
    diagnostics: dict[str, Any] = {
        **record,
        "train_direction": direction,
        "discovery_raw_rank_ic": float(direction * discovery_raw_ic.mean()),
        "validation_raw_rank_ic": float(raw_validation_oriented.mean()),
        "newey_west_t": nw_t,
        "one_sided_p": one_sided_p,
        "newey_west_lag": nw_lag,
        "validation_halfyear_count": half_count,
        "median_daily_unique_values": float(daily_unique.median()),
        "usable_date_ratio": float(usable_dates.mean()),
        "discovery_ic_days": int(len(discovery_oriented)),
        "validation_ic_days": int(len(validation_oriented)),
    }
    ic_daily = pd.DataFrame(
        {
            "discovery_neutral_ic": discovery_oriented,
            "validation_neutral_ic": validation_oriented,
            "validation_raw_ic": raw_validation_oriented,
            "validation_secondary_ic": secondary_oriented,
        }
    )
    daily = ic_daily.join(portfolio_daily, how="outer")
    return {**diagnostics, **metrics}, daily


def hard_gate_failures(row: pd.Series, config: dict[str, Any]) -> list[str]:
    gates = config["hard_gates"]
    failures: list[str] = []
    if row["average_signal_coverage"] < gates["min_coverage"]:
        failures.append("coverage")
    if row["usable_date_ratio"] < 0.95:
        failures.append("usable_dates")
    if row["median_daily_unique_values"] < 30:
        failures.append("unique_values")
    if row["discovery_rank_ic"] < gates["min_discovery_rank_ic"]:
        failures.append("discovery_ic")
    if row["validation_rank_ic"] < gates["min_validation_rank_ic"]:
        failures.append("validation_ic")
    if row["positive_halfyear_ratio"] < gates["min_positive_halfyear_ratio"]:
        failures.append("halfyear_signs")
    if row["newey_west_t"] < gates["min_newey_west_t"]:
        failures.append("newey_west_t")
    if row["fdr_q"] > gates["max_fdr_q"]:
        failures.append("fdr_q")
    if (
        not math.isfinite(row["neutralization_retention"])
        or row["neutralization_retention"] < gates["min_neutralization_retention"]
    ):
        failures.append("neutralization_retention")
    library_correlation = row.get("max_abs_library_correlation")
    if (
        library_correlation is not None
        and math.isfinite(float(library_correlation))
        and float(library_correlation) >= gates["hard_duplicate_correlation"]
    ):
        failures.append("hard_duplicate")
    return failures


def exact_daily_duplicate_map(
    daily_outputs: dict[str, pd.DataFrame],
) -> tuple[dict[str, str], dict[str, str]]:
    signatures: dict[str, str] = {}
    clusters: dict[str, list[str]] = {}
    for factor_id, daily in daily_outputs.items():
        values = pd.util.hash_pandas_object(daily, index=True).values.tobytes()
        signature = hashlib.sha256(values).hexdigest()
        signatures[factor_id] = signature
        clusters.setdefault(signature, []).append(factor_id)
    duplicate_of: dict[str, str] = {}
    for members in clusters.values():
        if len(members) < 2:
            continue
        representative = sorted(members)[0]
        for factor_id in sorted(members)[1:]:
            duplicate_of[factor_id] = representative
    return signatures, duplicate_of


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", required=True)
    parser.add_argument("--factor", action="append")
    parser.add_argument("--registry")
    parser.add_argument(
        "--include-all-scripts",
        action="store_true",
        help="Audit-only escape hatch; never use this as an active-library definition.",
    )
    parser.add_argument("--output-dir")
    args = parser.parse_args()

    panel_path = Path(args.panel).resolve()
    manifest_path = panel_path.with_suffix(".manifest.json")
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing evaluator-input manifest: {manifest_path}")
    panel_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if panel_manifest.get("research_stage") != "factor_validation":
        raise RuntimeError("This evaluator only accepts a factor_validation input panel")

    records = load_factor_records(PROJECT_ROOT / "factor_script")
    if args.include_all_scripts and args.registry:
        raise ValueError("--include-all-scripts and --registry are mutually exclusive")
    if not args.include_all_scripts and (args.registry or not args.factor):
        registry_path = (
            Path(args.registry).resolve()
            if args.registry
            else PROJECT_ROOT / "data" / "libraries" / "local_research_provisional.json"
        )
        if registry_path.exists():
            registry_ids = load_registry_factor_ids(registry_path)
            records = [record for record in records if record["factor_id"] in registry_ids]
        elif not args.factor:
            raise FileNotFoundError(
                f"No active registry found at {registry_path}; pass --factor explicitly or "
                "use --include-all-scripts for a trajectory audit"
            )
    if args.factor:
        selected = set(args.factor)
        records = [
            record
            for record in records
            if record["factor_id"] in selected or record["factor_name"] in selected
        ]
    if not records:
        raise RuntimeError("No active factor records selected")

    output_dir = (
        Path(args.output_dir).resolve()
        if args.output_dir
        else PROJECT_ROOT
        / "local_research"
        / "results"
        / f"formal_primary_{panel_manifest['data_snapshot'].split('-')[-1]}_{pd.Timestamp.now():%Y%m%dT%H%M%S}"
    )
    output_dir.mkdir(parents=True, exist_ok=False)
    metadata = load_panel(panel_path)
    executor = FormulaExecutor(
        str(panel_path),
        start_date=20150101,
        end_date=20221231,
    )
    config = load_config()
    results: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    daily_outputs: dict[str, pd.DataFrame] = {}
    for position, record in enumerate(records, start=1):
        try:
            result, daily = evaluate_record(record, executor, metadata)
            score = score_record(result, config)
            results.append(
                {
                    **result,
                    **{
                        key: value
                        for key, value in score.items()
                        if key not in {"metric_points", "section_points", "section_available_weight"}
                    },
                    "score_components_json": json.dumps(score["metric_points"], sort_keys=True),
                }
            )
            daily_outputs[record["factor_id"]] = daily
            print(
                f"[{position}/{len(records)}] {record['factor_id']}: "
                f"discovery={result['discovery_rank_ic']:.4f} "
                f"validation={result['validation_rank_ic']:.4f}",
                flush=True,
            )
        except Exception as exc:
            failures.append({**record, "error": str(exc)})
            print(f"[{position}/{len(records)}] {record['factor_id']}: FAILED {exc}", flush=True)

    summary = pd.DataFrame(results)
    if not summary.empty:
        daily_signatures, duplicate_of = exact_daily_duplicate_map(daily_outputs)
        summary["exact_daily_signature"] = summary["factor_id"].map(daily_signatures)
        summary["duplicate_of"] = summary["factor_id"].map(duplicate_of)
        summary["fdr_q"] = bh_qvalues(summary["one_sided_p"])
        summary["hard_gate_failures"] = [
            ",".join(hard_gate_failures(row, config)) for _, row in summary.iterrows()
        ]
        is_duplicate = summary["duplicate_of"].notna()
        summary.loc[is_duplicate, "hard_gate_failures"] = summary.loc[
            is_duplicate, "hard_gate_failures"
        ].map(lambda value: ",".join(filter(None, [value, "exact_daily_duplicate"])))
        summary["passes_available_hard_gates"] = summary["hard_gate_failures"].eq("")
        summary["provisional_band"] = summary["normalized_observed_score"].map(
            lambda value: score_band(value, config)
        )
        summary["admission_status"] = "incomplete_transfer_and_economic_review"
        summary = summary.sort_values(
            ["passes_available_hard_gates", "validation_rank_ic"],
            ascending=[False, False],
        )
        summary.to_csv(output_dir / "factor_summary.csv", index=False)
        for factor_id, daily in daily_outputs.items():
            daily.to_parquet(output_dir / f"factor_{factor_id}_daily_metrics.parquet")
    (output_dir / "failures.json").write_text(
        json.dumps(failures, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    run_manifest = {
        "created_at": pd.Timestamp.now(tz="Asia/Shanghai").isoformat(),
        "evaluator_version": config["version"],
        "status": "primary_universe_only_no_admission",
        "panel": str(panel_path),
        "panel_sha256": panel_manifest["output_sha256"],
        "data_snapshot": panel_manifest["data_snapshot"],
        "universe_version": panel_manifest["universe_sha256"],
        "label_version": panel_manifest["label_version"],
        "factor_count": len(records),
        "completed": len(results),
        "failed": len(failures),
        "discovery": [str(DISCOVERY_START.date()), str(DISCOVERY_END.date())],
        "validation": [str(VALIDATION_START.date()), str(VALIDATION_END.date())],
        "unavailable_for_formal_admission": [
            "parameter_stability",
            "CSI500 transfer",
            "liquid all-A transfer",
            "library panel correlation",
            "economic PASS/CONDITIONAL/FAIL review",
        ],
    }
    (output_dir / "run_manifest.json").write_text(
        json.dumps(run_manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Saved primary evaluation to {output_dir}")


if __name__ == "__main__":
    main()
