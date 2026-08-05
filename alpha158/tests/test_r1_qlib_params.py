from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR / "src"))

from alpha158_research.r1_qlib_params import (  # noqa: E402
    cross_sectional_zscore_label,
    load_r1_config,
    validate_r1_config,
)


CONFIG_PATH = PROJECT_DIR / "config" / "r1_qlib_parameter_transfer_v1.json"


def test_r1_parameters_equal_qlib_r0_except_local_thread_count():
    config = load_r1_config(CONFIG_PATH)
    validate_r1_config(config)
    assert config["lightgbm"]["num_leaves"] == 210
    assert config["lightgbm"]["learning_rate"] == 0.2
    assert config["lightgbm"]["num_threads"] == 4
    assert config["selection"] == "validation_best_iteration_only"


def test_r1_has_the_five_purged_2021_to_2025_test_folds():
    config = load_r1_config(CONFIG_PATH)
    assert [fold["test_year"] for fold in config["rolling_folds"]] == [2021, 2022, 2023, 2024, 2025]


def test_qlib_style_label_zscore_is_computed_within_each_signal_date():
    frame = pd.DataFrame(
        {
            "signal_date": ["2021-01-08"] * 3 + ["2021-01-15"] * 3,
            "target_excess_return": [0.01, 0.02, 0.04, -0.03, 0.00, 0.06],
        }
    )
    normalized = cross_sectional_zscore_label(frame, "target_excess_return")
    assert normalized.groupby(frame["signal_date"]).mean().round(12).eq(0).all()
    assert normalized.groupby(frame["signal_date"]).std(ddof=0).round(12).eq(1).all()
