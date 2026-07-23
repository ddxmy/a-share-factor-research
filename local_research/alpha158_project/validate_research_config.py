#!/usr/bin/env python3
"""Validate the frozen Alpha158 research definition using only stdlib."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = PROJECT_DIR / "config" / "research_v1.json"


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate(config: dict[str, Any], *, check_paths: bool) -> list[str]:
    errors: list[str] = []

    require(config.get("schema_version") == "1.0", "schema_version must be 1.0", errors)
    require(config.get("status") == "frozen", "research status must be frozen", errors)

    data = config.get("data", {})
    formal = data.get("formal_source", {})
    audit = data.get("audit_source", {})
    require(formal.get("snapshot_id") == "tushare-silver-2015-01-05-2026-07-16-86b4445468cf2907",
            "formal data snapshot changed", errors)
    require(audit.get("formal_model_input") is False,
            "third-party DuckDB must not be formal model input", errors)
    require(data.get("formal_sample") == {
        "start": "2015-01-01",
        "end": "2025-12-31",
        "observation_after_end": "forward_observation_only",
    }, "formal sample must remain 2015-2025", errors)

    if check_paths:
        require(Path(formal.get("root", "")).is_dir(), "formal data-lake root does not exist", errors)
        require(Path(audit.get("path", "")).is_file(), "audit DuckDB does not exist", errors)

    universe = config.get("universe", {})
    require(universe.get("index_code") == "000300.SH", "universe must be CSI 300", errors)
    require(universe.get("membership_mode") == "point_in_time_effective_intervals",
            "universe must use point-in-time membership", errors)
    require(universe.get("current_membership_backfill_forbidden") is True,
            "current membership backfill must be forbidden", errors)
    require(universe.get("minimum_valid_history_trading_days") == 60,
            "minimum valid history must be 60 trading days", errors)

    sampling = config.get("sampling", {})
    require(sampling.get("frequency") == "weekly", "sampling must be weekly", errors)
    require(sampling.get("signal_time") == "last_trading_day_of_week_close",
            "signal time changed", errors)
    require(sampling.get("entry_time") == "next_trading_day_open",
            "entry must be next trading day open", errors)

    label = config.get("label", {})
    require(label.get("target") == "stock_return - benchmark_return",
            "target must be CSI 300 excess return", errors)
    require(label.get("purge_rule") ==
            "label_end_date_must_be_strictly_before_next_segment_start",
            "split purge must use label_end_date", errors)

    features = config.get("features", {})
    require(features.get("library") == "Microsoft_Qlib_Alpha158",
            "feature library must be official Qlib Alpha158", errors)
    require(features.get("expected_count") == 158, "feature count must be 158", errors)
    require(features.get("custom_factors_allowed") is False,
            "custom factors must remain disabled in v1", errors)
    require(features.get("fundamental_features_allowed") is False,
            "fundamental features must remain disabled in v1", errors)

    neutralization = config.get("neutralization", {})
    require(neutralization.get("target") == "model_prediction_score",
            "neutralization must target model scores", errors)
    require(neutralization.get("claim_as_full_barra_model") is False,
            "score residualization cannot be claimed as full Barra", errors)

    models = config.get("models", {})
    require(models.get("allowed") == ["ridge", "lightgbm"],
            "v1 models must be exactly Ridge and LightGBM", errors)
    require(models.get("selection_metric") == "validation_mean_weekly_rank_ic",
            "model selection metric changed", errors)
    require(models.get("test_data_for_model_selection_forbidden") is True,
            "test data must remain locked for model selection", errors)

    expected_folds = [
        (list(range(2015, 2020)), 2020, 2021),
        (list(range(2016, 2021)), 2021, 2022),
        (list(range(2017, 2022)), 2022, 2023),
        (list(range(2018, 2023)), 2023, 2024),
        (list(range(2019, 2024)), 2024, 2025),
    ]
    folds = config.get("rolling_folds", [])
    require(len(folds) == len(expected_folds), "there must be five rolling folds", errors)
    for index, expected in enumerate(expected_folds):
        if index >= len(folds):
            break
        fold = folds[index]
        observed = (
            fold.get("train_years"),
            fold.get("validation_year"),
            fold.get("test_year"),
        )
        require(observed == expected, f"rolling fold {index + 1} changed", errors)

    evaluation = config.get("signal_evaluation", {})
    require(evaluation.get("primary_metric") == "weekly_spearman_rank_ic",
            "primary signal metric must be weekly Spearman Rank IC", errors)
    require(evaluation.get("newey_west_lags") == 4,
            "Newey-West lag must remain 4 in v1", errors)

    portfolio = config.get("portfolio", {})
    require(portfolio.get("diagnostic_groups") == 5,
            "diagnostic grouping must use five groups", errors)
    require(portfolio.get("long_portfolio", {}).get("selection") ==
            "top_50_by_neutralized_prediction_score",
            "long portfolio must be neutralized-score Top50", errors)
    require(portfolio.get("one_way_cost_bps_scenarios") == [0, 10, 20],
            "cost scenarios must be 0/10/20 bps per side", errors)

    excluded = set(config.get("excluded_from_v1", []))
    require({"previously_mined_custom_factors", "XGBoost", "neural_networks"} <= excluded,
            "v1 exclusion list lost a core scope boundary", errors)

    expected_gates = [
        "G0_research_definition",
        "G1_data_and_point_in_time_universe",
        "G2_alpha158_qlib_parity",
        "G3_weekly_label_and_purged_splits",
        "G4_ridge_baseline",
        "G5_lightgbm",
        "G6_signal_evaluation",
        "G7_tradable_backtest",
        "G8_report_and_interview_materials",
    ]
    require(config.get("gates") == expected_gates, "research gates changed", errors)

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--skip-path-checks",
        action="store_true",
        help="Validate frozen definitions without checking local data paths.",
    )
    args = parser.parse_args()

    try:
        config = json.loads(args.config.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: cannot load config: {exc}")
        return 2

    errors = validate(config, check_paths=not args.skip_path_checks)
    if errors:
        print(f"FAIL: {len(errors)} validation error(s)")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"PASS: frozen research config is internally consistent: {args.config}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
