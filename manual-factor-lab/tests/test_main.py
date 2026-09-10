"""End-to-end contracts for the single-factor command and report bundle."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import factor_modules  # noqa: E402
import factors  # noqa: E402
from a_share_factor_research import main as main_module  # noqa: E402
from a_share_factor_research import performance_records  # noqa: E402
from a_share_factor_research.main import run_factor  # noqa: E402


PROFILE = PROJECT_ROOT / "config" / "daily_baseline.yaml"
REQUIRED_FILES = {
    "summary.json",
    "data_quality.csv",
    "ic_summary.csv",
    "ic_daily.csv",
    "portfolio_summary.csv",
    "nav.csv",
    "report.html",
}
REQUIRED_FIGURES = {
    "cumulative_rank_ic.png",
    "annual_ic.png",
    "top_k_nav.png",
}


@pytest.fixture
def configured_data_root(tmp_path: Path) -> Path:
    """Create a complete private catalog large enough for every profile."""
    derived = tmp_path / "private-data" / "derived"
    (derived / "universe").mkdir(parents=True)
    (derived / "benchmark").mkdir()
    (derived / "tradability").mkdir()

    dates = pd.bdate_range("2024-01-02", periods=65)
    security_ids = [f"{number:06d}.SZ" for number in range(1, 33)]
    daily_records = []
    for security_number, security_id in enumerate(security_ids, start=1):
        for day_number, trade_date in enumerate(dates):
            adjusted_open = 10.0 + security_number / 10 + day_number * (
                0.01 + security_number / 10000
            )
            daily_records.append(
                {
                    "trade_date": trade_date,
                    "security_id": security_id,
                    "adjusted_open": adjusted_open,
                    "adjusted_close": adjusted_open * (1 + security_number / 100000),
                }
            )
    daily = pd.DataFrame.from_records(daily_records)
    daily.to_parquet(derived / "daily_panel.parquet", index=False)
    daily[["trade_date", "security_id"]].assign(is_member=True).to_parquet(
        derived / "universe" / "pit_csi300.parquet", index=False
    )
    daily[["trade_date", "security_id"]].assign(tradable_next_open=True).to_parquet(
        derived / "tradability" / "open_eligibility.parquet", index=False
    )
    pd.DataFrame(
        {
            "trade_date": dates,
            "adjusted_open": [100.0 + day_number * 0.1 for day_number in range(len(dates))],
        }
    ).to_parquet(derived / "benchmark" / "csi300_open.parquet", index=False)
    return derived.parent


@pytest.fixture
def implemented_rev5(monkeypatch):
    """Stand in only for the researcher formula, below the real registry boundary."""
    calls = []

    def compute_rev5(panel: pd.DataFrame) -> pd.DataFrame:
        calls.append(len(panel))
        return panel[["trade_date", "security_id"]].assign(
            raw_value=pd.to_numeric(panel["adjusted_close"])
        )

    monkeypatch.setattr(factor_modules.rev5, "compute", compute_rev5)
    return calls


def test_main_writes_required_artifacts_and_audit_metadata(
    configured_data_root: Path, implemented_rev5, monkeypatch
):
    """Removing any required report or audit field must break this contract."""
    monkeypatch.setenv("A_SHARE_DATA_ROOT", str(configured_data_root))
    output_root = configured_data_root / "runs"

    output = run_factor("REV5", PROFILE, "2024-01-02", "2024-02-19", output_root)

    assert output.is_relative_to(configured_data_root)
    assert REQUIRED_FILES <= {path.name for path in output.iterdir()}
    assert REQUIRED_FIGURES <= {path.name for path in (output / "figures").iterdir()}
    assert implemented_rev5 == [35 * 32]

    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert summary["factor_id"] == "REV5"
    assert summary["registry"]["pre_registered_direction"] == "negative"
    assert summary["profile"]["horizons"] == [1, 5, 20]
    assert "git_revision" in summary
    assert set(summary["input_sha256"]) == {
        "profile",
        "factor_registry",
        "daily_panel",
        "pit_csi300",
        "csi300_open",
        "open_eligibility",
    }
    assert all(
        len(digest) == 64 and int(digest, 16) >= 0
        for digest in summary["input_sha256"].values()
    )
    assert summary["input_sha256"]["profile"] == hashlib.sha256(
        PROFILE.read_bytes()
    ).hexdigest()


def test_main_updates_private_scoreboard_only_after_complete_publication(
    configured_data_root: Path, implemented_rev5, monkeypatch
):
    """Skipping the post-publication recorder must leave a completed run unindexed."""
    monkeypatch.setenv("A_SHARE_DATA_ROOT", str(configured_data_root))

    output = run_factor("REV5", PROFILE, "2024-01-02", "2024-02-01")

    scoreboard = pd.read_parquet(configured_data_root / "factor_scoreboard.parquet")
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert scoreboard[["factor_id", "run_id", "relative_run_path"]].to_dict(
        "records"
    ) == [
        {
            "factor_id": "REV5",
            "run_id": summary["run_id"],
            "relative_run_path": output.relative_to(configured_data_root).as_posix(),
        }
    ]
    assert summary["run_type"] == "formal"
    assert scoreboard.loc[0, "run_type"] == "formal"


def test_main_rejects_noncanonical_output_root_before_calculation(
    configured_data_root: Path, implemented_rev5, monkeypatch
):
    """A noncanonical output tree must not publish an unrecordable successful run."""
    monkeypatch.setenv("A_SHARE_DATA_ROOT", str(configured_data_root))

    with pytest.raises(ValueError, match="A_SHARE_DATA_ROOT/runs"):
        run_factor(
            "REV5",
            PROFILE,
            "2024-01-02",
            "2024-02-19",
            configured_data_root / "custom-runs",
        )

    assert implemented_rev5 == []


def test_main_marks_custom_profile_experimental_and_excludes_it_from_factor_card(
    configured_data_root: Path, implemented_rev5, monkeypatch, tmp_path: Path
):
    """A copied custom profile must not replace the baseline's formal factor card."""
    monkeypatch.setenv("A_SHARE_DATA_ROOT", str(configured_data_root))
    custom_profile = tmp_path / "custom_profile.yaml"
    custom_profile.write_text(PROFILE.read_text(encoding="utf-8"), encoding="utf-8")

    formal_run = run_factor("REV5", PROFILE, "2024-01-02", "2024-02-19")
    experimental_run = run_factor(
        "REV5", custom_profile, "2024-01-02", "2024-02-19"
    )

    formal_summary = json.loads((formal_run / "summary.json").read_text(encoding="utf-8"))
    experimental_summary = json.loads(
        (experimental_run / "summary.json").read_text(encoding="utf-8")
    )
    assert formal_summary["run_type"] == "formal"
    assert experimental_summary["run_type"] == "experimental"
    card = (configured_data_root / "factor_cards" / "REV5.html").read_text(
        encoding="utf-8"
    )
    assert formal_run.name in card
    assert experimental_run.name not in card


def test_main_does_not_create_scoreboard_when_report_publication_fails(
    configured_data_root: Path, implemented_rev5, monkeypatch
):
    """Moving recording before publication must create forbidden comparison state."""
    monkeypatch.setenv("A_SHARE_DATA_ROOT", str(configured_data_root))

    def fail_publication(*args, **kwargs):
        raise RuntimeError("publish failed")

    monkeypatch.setattr(main_module, "_publish_atomically", fail_publication)

    with pytest.raises(RuntimeError, match="publish failed"):
        run_factor("REV5", PROFILE, "2024-01-02", "2024-02-19")

    assert not (configured_data_root / "factor_scoreboard.parquet").exists()


def test_main_preserves_immutable_run_when_scoreboard_recording_fails(
    configured_data_root: Path, implemented_rev5, monkeypatch
):
    """Recorder errors must surface without rolling back the completed run bundle."""
    monkeypatch.setenv("A_SHARE_DATA_ROOT", str(configured_data_root))
    published_snapshot = {}

    def fail_recording(data_root: Path, run_directory: Path) -> None:
        published_snapshot["files"] = {
            path.relative_to(run_directory).as_posix(): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in run_directory.rglob("*")
            if path.is_file()
        }
        raise RuntimeError("scoreboard recording failed")

    monkeypatch.setattr(performance_records, "record_successful_run", fail_recording)

    with pytest.raises(RuntimeError, match="scoreboard recording failed"):
        run_factor("REV5", PROFILE, "2024-01-02", "2024-02-19")

    factor_directory = configured_data_root / "runs" / "REV5"
    published_runs = [path for path in factor_directory.iterdir() if path.is_dir()]
    assert len(published_runs) == 1
    published_run = published_runs[0]
    assert REQUIRED_FILES <= {path.name for path in published_run.iterdir()}
    assert REQUIRED_FIGURES <= {
        path.name for path in (published_run / "figures").iterdir()
    }
    summary = json.loads((published_run / "summary.json").read_text(encoding="utf-8"))
    assert summary["run_id"] == published_run.name
    preserved_snapshot = {
        path.relative_to(published_run).as_posix(): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in published_run.rglob("*")
        if path.is_file()
    }
    assert preserved_snapshot == published_snapshot["files"]
    assert not (configured_data_root / "factor_scoreboard.parquet").exists()


def test_main_isolates_factor_inputs_and_uses_history_and_forward_buffers(
    configured_data_root: Path, monkeypatch
):
    """Future labels must not leak into formulas while requested signals keep their buffers."""
    monkeypatch.setenv("A_SHARE_DATA_ROOT", str(configured_data_root))
    observed = {}

    def compute_rev5(panel: pd.DataFrame) -> pd.DataFrame:
        observed["columns"] = set(panel.columns)
        observed["first_date"] = panel["trade_date"].min()
        observed["last_date"] = panel["trade_date"].max()
        return panel[["trade_date", "security_id"]].assign(
            raw_value=pd.to_numeric(panel["adjusted_close"])
        )

    monkeypatch.setattr(factor_modules.rev5, "compute", compute_rev5)
    monkeypatch.setattr(performance_records, "record_successful_run", lambda *args: None)
    output = run_factor(
        "REV5",
        PROFILE,
        "2024-01-09",
        "2024-01-16",
        configured_data_root / "runs",
    )

    forbidden = {
        "entry_date",
        "basic_eligible",
        "tradable_next_open",
        "label_excess_o2o_1d",
        "label_excess_o2o_5d",
        "label_excess_o2o_20d",
        "label_end_date_1d",
        "label_end_date_5d",
        "label_end_date_20d",
    }
    assert not observed["columns"].intersection(forbidden)
    assert observed["first_date"] == pd.Timestamp("2024-01-02")
    assert observed["last_date"] == pd.Timestamp("2024-01-16")

    nav = pd.read_csv(output / "nav.csv", parse_dates=["signal_date"])
    assert nav["signal_date"].between("2024-01-09", "2024-01-16").all()
    ic_daily = pd.read_csv(output / "ic_daily.csv", parse_dates=["signal_date"])
    assert ic_daily["signal_date"].between("2024-01-09", "2024-01-16").all()
    data_quality = pd.read_csv(output / "data_quality.csv").set_index("metric")
    assert data_quality.loc["signal_dates", "value"] == 6
    summary = pd.read_csv(output / "portfolio_summary.csv")
    top_k = summary.loc[
        (summary["portfolio_kind"] == "top_k_long")
        & (summary["return_type"].isin(["gross", "net"]))
    ]
    assert set(top_k["horizon_days"]) == {1, 5, 20}
    assert top_k["annualized_return"].notna().all()


def test_main_rejects_output_root_outside_private_data_root(
    configured_data_root: Path, implemented_rev5, monkeypatch, tmp_path: Path
):
    """Weakening containment must not allow a private run to escape its root."""
    monkeypatch.setenv("A_SHARE_DATA_ROOT", str(configured_data_root))

    with pytest.raises(ValueError, match="A_SHARE_DATA_ROOT"):
        run_factor("REV5", PROFILE, "2024-01-02", "2024-02-19", tmp_path / "escaped")

    assert implemented_rev5 == []


def test_main_rejects_factor_directory_symlink_escape_before_calculation(
    configured_data_root: Path, implemented_rev5, monkeypatch, tmp_path: Path
):
    """An in-root symlink must not redirect factor artifacts outside the root."""
    monkeypatch.setenv("A_SHARE_DATA_ROOT", str(configured_data_root))
    output_root = configured_data_root / "runs"
    output_root.mkdir()
    outside = tmp_path / "outside-private-root"
    outside.mkdir()
    (output_root / "REV5").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="A_SHARE_DATA_ROOT"):
        run_factor("REV5", PROFILE, "2024-01-02", "2024-02-19", output_root)

    assert implemented_rev5 == []
    assert list(outside.iterdir()) == []


def test_main_fails_before_calculation_for_missing_catalog(
    implemented_rev5, monkeypatch, tmp_path: Path
):
    """Moving catalog checks after calculation must trigger this regression."""
    monkeypatch.setenv("A_SHARE_DATA_ROOT", str(tmp_path))

    with pytest.raises(FileNotFoundError, match="daily_panel.parquet"):
        run_factor("REV5", PROFILE, "2024-01-02", "2024-02-01", tmp_path / "runs")

    assert implemented_rev5 == []


def test_main_validates_factor_before_catalog(
    monkeypatch, tmp_path: Path
):
    """Unknown factor IDs must not be obscured by downstream catalog errors."""
    monkeypatch.setenv("A_SHARE_DATA_ROOT", str(tmp_path))

    with pytest.raises(ValueError, match="UNKNOWN"):
        run_factor("UNKNOWN", PROFILE, "2024-01-02", "2024-02-01", tmp_path / "runs")


def test_documented_module_command_is_importable_from_repository_root():
    """Breaking the root-level module path must make the documented CLI fail."""
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)

    completed = subprocess.run(
        [sys.executable, "-m", "a_share_factor_research.main", "--help"],
        cwd=REPOSITORY_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "--factor" in completed.stdout
