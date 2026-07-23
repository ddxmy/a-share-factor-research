#!/usr/bin/env python3
"""Blind discovery-only screen for a frozen batch of factor formulas.

This program intentionally refuses to inspect observations after 2020-12-31.
Its outputs are research diagnostics, not formal quality scores or admissions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from evaluate_factors import (
    PROJECT_ROOT,
    FormulaExecutor,
    daily_ic,
    halfyear_statistics,
    load_factor_records,
    neutralize_one_day,
    portfolio_diagnostics,
)


DISCOVERY_START = pd.Timestamp("2016-01-01")
DISCOVERY_END = pd.Timestamp("2020-12-31")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_discovery_metadata(path: Path) -> pd.DataFrame:
    """Read only warm-up/discovery rows; never materialize factor-validation labels."""
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
    panel = pd.read_parquet(
        path,
        columns=columns,
        filters=[("dt", ">=", pd.Timestamp("2015-01-01")), ("dt", "<=", DISCOVERY_END)],
    )
    panel["dt"] = pd.to_datetime(panel["dt"])
    panel["Ticker"] = panel["Ticker"].astype(str)
    panel["log_float_mkt_cap"] = np.log(
        pd.to_numeric(panel["float_mkt_cap"], errors="coerce").where(lambda value: value > 0)
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
    panel = panel.loc[panel["dt"].between(DISCOVERY_START, DISCOVERY_END)]
    return panel.set_index(["dt", "Ticker"]).sort_index()


def preprocess_discovery_signal(signal: pd.DataFrame, metadata: pd.DataFrame) -> pd.DataFrame:
    raw = signal.stack(future_stack=True).rename("raw_signal")
    raw.index.names = ["dt", "Ticker"]
    joined = metadata.join(raw, how="left")
    joined.loc[~joined["signal_eligible"], "raw_signal"] = np.nan
    joined["neutral_signal"] = (
        joined.groupby(level="dt", group_keys=False)
        .apply(neutralize_one_day, include_groups=False)
        .reindex(joined.index)
    )
    return joined


def screen_one(
    record: dict[str, str], executor: FormulaExecutor, metadata: pd.DataFrame
) -> tuple[dict[str, Any], pd.Series, pd.DataFrame]:
    signal = executor.compute(record["formula"])
    prepared = preprocess_discovery_signal(signal, metadata)
    evaluable = prepared.loc[prepared["primary_evaluable"]].copy()
    neutral_ic = daily_ic(evaluable, "neutral_signal", "next_open_to_close")
    raw_ic = daily_ic(evaluable, "raw_signal", "next_open_to_close")
    if neutral_ic.empty:
        raise RuntimeError("No usable discovery IC series")

    direction = 1 if neutral_ic.mean() >= 0 else -1
    oriented = direction * neutral_ic
    raw_oriented = direction * raw_ic
    half_ratio, worst_half, half_count = halfyear_statistics(oriented)

    # Direction is selected on discovery itself, so this is a two-sided diagnostic.
    from calibrate_scores import newey_west_t

    nw_t, _, nw_lag = newey_west_t(oriented)
    two_sided_p = float(2.0 * stats.norm.sf(abs(nw_t)))
    portfolio, portfolio_daily = portfolio_diagnostics(evaluable, direction)

    eligible_counts = metadata.loc[metadata["primary_evaluable"]].groupby(level="dt").size()
    factor_counts = prepared.loc[
        prepared["primary_evaluable"] & prepared["neutral_signal"].notna()
    ].groupby(level="dt").size()
    coverage = factor_counts / eligible_counts.reindex(factor_counts.index)
    daily_unique = prepared["neutral_signal"].groupby(level="dt").nunique()
    usable_dates = factor_counts.ge(50)
    raw_abs = abs(float(raw_oriented.mean()))
    neutral_abs = abs(float(oriented.mean()))

    metrics: dict[str, Any] = {
        **record,
        "train_direction": direction,
        "discovery_rank_ic": float(oriented.mean()),
        "discovery_raw_rank_ic": float(raw_oriented.mean()),
        "discovery_icir": float(oriented.mean() / (oriented.std(ddof=1) + 1e-12)),
        "annualized_discovery_icir": float(
            oriented.mean() / (oriented.std(ddof=1) + 1e-12) * np.sqrt(252)
        ),
        "monthly_ic_hit_rate": float(
            oriented.groupby(oriented.index.to_period("M")).mean().gt(0).mean()
        ),
        "positive_halfyear_ratio": half_ratio,
        "worst_halfyear_ic": worst_half,
        "halfyear_count": half_count,
        "newey_west_t": float(nw_t),
        "two_sided_p": two_sided_p,
        "newey_west_lag": int(nw_lag),
        "neutralization_retention": neutral_abs / raw_abs if raw_abs > 1e-12 else math.nan,
        "average_signal_coverage": float(coverage.mean()),
        "usable_date_ratio": float(usable_dates.mean()),
        "median_daily_unique_values": float(daily_unique.median()),
        "discovery_ic_days": int(len(oriented)),
        **portfolio,
    }
    signal_for_correlation = direction * prepared["neutral_signal"]
    ic_daily = pd.DataFrame({"discovery_neutral_ic": oriented})
    return metrics, signal_for_correlation, ic_daily.join(portfolio_daily, how="outer")


def average_abs_daily_spearman(left: pd.Series, right: pd.Series) -> float:
    joined = pd.concat({"left": left, "right": right}, axis=1).dropna()
    if joined.empty:
        return math.nan

    def one_day(day: pd.DataFrame) -> float:
        if len(day) < 30 or day["left"].nunique() < 2 or day["right"].nunique() < 2:
            return math.nan
        return abs(float(day["left"].corr(day["right"], method="spearman")))

    return float(joined.groupby(level="dt").apply(one_day).mean())


def average_abs_daily_spearman_matrix(signals: dict[str, pd.Series]) -> pd.DataFrame:
    """Average absolute daily Spearman matrix, computed once per date."""
    ids = sorted(signals)
    wide = pd.concat({factor_id: signals[factor_id] for factor_id in ids}, axis=1)
    sums = np.zeros((len(ids), len(ids)), dtype=np.float64)
    counts = np.zeros((len(ids), len(ids)), dtype=np.int32)
    for _, day in wide.groupby(level="dt", sort=True):
        correlation = day.corr(method="spearman", min_periods=30).abs().to_numpy(dtype=float)
        valid = np.isfinite(correlation)
        sums[valid] += correlation[valid]
        counts[valid] += 1
    average = np.divide(
        sums,
        counts,
        out=np.full_like(sums, np.nan),
        where=counts > 0,
    )
    np.fill_diagonal(average, 1.0)
    return pd.DataFrame(average, index=ids, columns=ids)


def discovery_failures(row: pd.Series) -> list[str]:
    failures: list[str] = []
    if row["average_signal_coverage"] < 0.95:
        failures.append("coverage")
    if row["usable_date_ratio"] < 0.95:
        failures.append("usable_dates")
    if row["median_daily_unique_values"] < 30:
        failures.append("unique_values")
    return failures


def discovery_tier(row: pd.Series) -> str:
    if discovery_failures(row):
        return "invalid"
    if (
        row["discovery_rank_ic"] >= 0.01
        and row["positive_halfyear_ratio"] >= 0.70
        and row["newey_west_t"] >= 2.5
    ):
        return (
            "discovery_implementation"
            if row["net_sharpe_10bps"] > 0
            else "discovery_qualified"
        )
    if row["discovery_rank_ic"] >= 0.005 and row["positive_halfyear_ratio"] >= 0.60:
        return "discovery_research"
    return "discovery_fail"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", required=True)
    parser.add_argument("--campaign-manifest", required=True)
    parser.add_argument("--pack-manifest", required=True)
    parser.add_argument("--lint-results", required=True)
    parser.add_argument("--factor", action="append", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    panel_path = Path(args.panel).resolve()
    manifest_path = panel_path.with_suffix(".manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("research_stage") != "discovery":
        raise RuntimeError("Expected a discovery-only input panel")
    if manifest.get("label_visibility") != "2016-01-01_to_2020-12-31_only":
        raise RuntimeError("Discovery label-visibility policy is missing or unexpected")
    if manifest.get("warmup_labels_masked") is not True:
        raise RuntimeError("Warm-up labels must be masked in a discovery panel")
    if pd.Timestamp(manifest.get("last_date")) > DISCOVERY_END:
        raise RuntimeError("Discovery panel contains observations after 2020-12-31")
    campaign_path = Path(args.campaign_manifest).resolve()
    campaign = json.loads(campaign_path.read_text(encoding="utf-8"))
    if campaign.get("status") != "discovery_open_validation_sealed":
        raise RuntimeError("Campaign is not open for discovery with validation sealed")
    if campaign.get("discovery_panel_sha256") != manifest.get("output_sha256"):
        raise RuntimeError("Campaign and discovery panel hashes differ")
    if campaign.get("discovery_dates") != ["2016-01-01", "2020-12-31"]:
        raise RuntimeError("Unexpected campaign discovery dates")

    pack_path = Path(args.pack_manifest).resolve()
    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    if pack.get("status") != "sealed_before_discovery":
        raise RuntimeError("Pack must be sealed before discovery")
    if pack.get("campaign_hash") != campaign.get("campaign_hash"):
        raise RuntimeError("Pack and campaign hashes differ")
    if sha256_file(Path(pack["discovery_evaluator_path"])) != pack["discovery_evaluator_sha256"]:
        raise RuntimeError("Discovery evaluator changed after pack seal")
    if sha256_file(Path(pack["proposals_path"])) != pack["proposals_sha256"]:
        raise RuntimeError("Proposals changed after pack seal")
    lint_path = Path(args.lint_results).resolve()
    lint = pd.read_csv(lint_path)
    if len(lint) != 40 or lint["candidate_id"].nunique() != 40:
        raise RuntimeError("Lint results must cover all 40 sealed proposals")
    lint_hashes = dict(zip(lint["candidate_id"], lint["formula_hash"], strict=True))
    if any(
        lint_hashes.get(candidate_id) != formula_hash
        for candidate_id, formula_hash in pack["candidate_formula_hashes"].items()
    ):
        raise RuntimeError("Lint formula hashes differ from the sealed pack")

    requested = set(args.factor)
    valid_ids = set(lint.loc[lint["status"].eq("valid"), "candidate_id"].astype(str))
    if requested != valid_ids:
        raise RuntimeError("Discovery factor list must equal the lint-valid sealed candidates")
    records = [
        record
        for record in load_factor_records(PROJECT_ROOT / "factor_script")
        if record["factor_id"] in requested or record["factor_name"] in requested
    ]
    if len(records) != len(requested):
        found = {record["factor_id"] for record in records} | {
            record["factor_name"] for record in records
        }
        raise RuntimeError(f"Missing requested factors: {sorted(requested - found)}")

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    metadata = load_discovery_metadata(panel_path)
    executor = FormulaExecutor(str(panel_path), start_date=20150101, end_date=20201231)

    results: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    signals: dict[str, pd.Series] = {}
    for position, record in enumerate(records, start=1):
        try:
            metrics, signal, daily = screen_one(record, executor, metadata)
            results.append(metrics)
            signals[record["factor_id"]] = signal
            daily.to_parquet(output_dir / f"factor_{record['factor_id']}_discovery_daily.parquet")
            print(
                f"[{position}/{len(records)}] {record['factor_id']}: "
                f"IC={metrics['discovery_rank_ic']:.4f} "
                f"NW={metrics['newey_west_t']:.2f} "
                f"net10={metrics['net_sharpe_10bps']:.2f}",
                flush=True,
            )
        except Exception as exc:
            failures.append({**record, "error": str(exc)})
            print(f"[{position}/{len(records)}] {record['factor_id']}: FAILED {exc}", flush=True)

    summary = pd.DataFrame(results)
    correlations: list[dict[str, Any]] = []
    correlation_matrix = average_abs_daily_spearman_matrix(signals)
    ids = list(correlation_matrix.index)
    for left_pos, left_id in enumerate(ids):
        for right_id in ids[left_pos + 1:]:
            correlations.append(
                {
                    "left_factor_id": left_id,
                    "right_factor_id": right_id,
                    "average_abs_daily_spearman": float(
                        correlation_matrix.loc[left_id, right_id]
                    ),
                }
            )
    correlation_frame = pd.DataFrame(correlations)
    if not summary.empty:
        from calibrate_scores import bh_qvalues

        summary["discovery_bh_q"] = bh_qvalues(summary["two_sided_p"])
        summary["discovery_screen_failures"] = [
            ",".join(discovery_failures(row)) for _, row in summary.iterrows()
        ]
        summary["discovery_tier"] = [discovery_tier(row) for _, row in summary.iterrows()]
        if correlation_frame.empty:
            summary["max_abs_batch_correlation"] = 0.0
        else:
            left = correlation_frame.rename(columns={"left_factor_id": "factor_id"})[
                ["factor_id", "average_abs_daily_spearman"]
            ]
            right = correlation_frame.rename(columns={"right_factor_id": "factor_id"})[
                ["factor_id", "average_abs_daily_spearman"]
            ]
            max_correlation = pd.concat([left, right]).groupby("factor_id")[
                "average_abs_daily_spearman"
            ].max()
            summary["max_abs_batch_correlation"] = summary["factor_id"].map(
                max_correlation
            ).fillna(0.0)
        summary["implementation_ready_10bps"] = summary["net_sharpe_10bps"].gt(0)
        summary["discovery_survivor"] = (
            summary["discovery_tier"].isin(
                ["discovery_research", "discovery_qualified", "discovery_implementation"]
            )
            & summary["max_abs_batch_correlation"].lt(0.50)
        )
        summary["passes_discovery_screen"] = summary["discovery_tier"].ne("invalid")
        summary = summary.sort_values(
            ["discovery_survivor", "discovery_rank_ic", "net_sharpe_10bps"],
            ascending=[False, False, False],
        )
        summary.to_csv(output_dir / "discovery_summary.csv", index=False)
    correlation_frame.to_csv(output_dir / "discovery_correlations.csv", index=False)
    (output_dir / "failures.json").write_text(
        json.dumps(failures, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    run_manifest = {
        "created_at": pd.Timestamp.now(tz="Asia/Shanghai").isoformat(),
        "stage": "discovery_screen_only",
        "campaign_version": campaign["campaign_version"],
        "campaign_hash": campaign["campaign_hash"],
        "campaign_manifest": str(campaign_path),
        "pack_manifest": str(pack_path),
        "pack_manifest_sha256": sha256_file(pack_path),
        "lint_results": str(lint_path),
        "lint_results_sha256": sha256_file(lint_path),
        "validation_labels_opened": False,
        "metadata_read_end": str(DISCOVERY_END.date()),
        "discovery": [str(DISCOVERY_START.date()), str(DISCOVERY_END.date())],
        "panel": str(panel_path),
        "panel_sha256": manifest["output_sha256"],
        "data_snapshot": manifest["data_snapshot"],
        "requested_factors": sorted(requested),
        "completed": len(results),
        "failed": len(failures),
        "warning": "Discovery diagnostics are not formal scores or admissions.",
    }
    (output_dir / "run_manifest.json").write_text(
        json.dumps(run_manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Saved blind discovery screen to {output_dir}")


if __name__ == "__main__":
    main()
