"""Persistence contracts for immutable-run-derived factor performance records."""

from __future__ import annotations

import json
import multiprocessing
from pathlib import Path

import duckdb
import pandas as pd
import pytest

import a_share_factor_research.performance_records as records_module
from a_share_factor_research.performance_records import (
    load_scoreboard,
    record_successful_run,
)
from a_share_factor_research.reporting import REQUIRED_ARTIFACTS


HORIZONS = (1, 5, 20)


def write_complete_run(
    data_root: Path,
    *,
    factor_id: str = "REV5",
    run_id: str = "run-001",
    created_at: str = "2026-08-14T01:02:03+00:00",
    run_type: str = "formal",
) -> Path:
    """Write a production-complete immutable report bundle."""
    run_directory = data_root / "runs" / factor_id / run_id
    run_directory.mkdir(parents=True)
    summary = {
        "schema_version": 1,
        "factor_id": factor_id,
        "run_id": run_id,
        "created_at_utc": created_at,
        "decision": "Review",
        "run_type": run_type,
        "date_range": {"start": "2021-01-01", "end": "2025-12-31"},
        "registry": {
            "factor_id": factor_id,
            "pre_registered_direction": "negative",
            "status": "candidate",
        },
        "profile": {
            "horizons": list(HORIZONS),
            "holding_period_days": list(HORIZONS),
            "top_k": 50,
            "one_way_cost_bps": 10.0,
        },
        "input_sha256": {"profile": "a" * 64},
        "git_revision": "abc123",
        "artifacts": list(REQUIRED_ARTIFACTS),
    }
    (run_directory / "summary.json").write_text(
        json.dumps(summary), encoding="utf-8"
    )

    ic_rows = []
    for horizon in HORIZONS:
        for eligibility, offset in (("basic", 0.0), ("tradable", 0.01)):
            ic_rows.append(
                {
                    "horizon_days": horizon,
                    "eligibility": eligibility,
                    "sample": "overlapping",
                    "year": pd.NA,
                    "n_observations": 500 + horizon,
                    "mean_pearson_ic": horizon / 1000 + offset,
                    "pearson_icir": horizon / 100 + offset,
                    "mean_rank_ic": horizon / 100 + offset,
                    "rank_icir": horizon / 10 + offset,
                    "hac_t_stat": 2.0 + horizon / 100,
                    "hac_one_sided_p_value": 0.04,
                }
            )
        # A robustness row must never displace the formal overlapping metric.
        ic_rows.append(
            {
                "horizon_days": horizon,
                "eligibility": "basic",
                "sample": "non_overlapping",
                "year": pd.NA,
                "n_observations": 99,
                "mean_pearson_ic": 99.0,
                "pearson_icir": 99.0,
                "mean_rank_ic": 99.0,
                "rank_icir": 99.0,
                "hac_t_stat": 99.0,
                "hac_one_sided_p_value": 0.0,
            }
        )
    pd.DataFrame(ic_rows).to_csv(run_directory / "ic_summary.csv", index=False)

    portfolio_rows = []
    for horizon in HORIZONS:
        for return_type, offset in (("gross", 0.0), ("net", -0.01)):
            portfolio_rows.append(
                {
                    "horizon_days": horizon,
                    "periods_per_year": {1: 252, 5: 52, 20: 12}[horizon],
                    "portfolio": "top_50",
                    "portfolio_kind": "top_k_long",
                    "is_diagnostic": False,
                    "return_type": return_type,
                    "n_periods": 100,
                    "n_evaluable_periods": 98,
                    "annualized_return": horizon / 100 + offset,
                    "volatility": 0.2,
                    "sharpe": horizon / 10 + offset,
                    "max_drawdown": -0.1,
                    "mean_turnover": 0.25,
                }
            )
        portfolio_rows.append(
            {
                "horizon_days": horizon,
                "periods_per_year": {1: 252, 5: 52, 20: 12}[horizon],
                "portfolio": "top_bottom",
                "portfolio_kind": "diagnostic_long_short",
                "is_diagnostic": True,
                "return_type": "net",
                "n_periods": 100,
                "n_evaluable_periods": 98,
                "annualized_return": 999.0,
                "volatility": 999.0,
                "sharpe": 999.0,
                "max_drawdown": -0.99,
                "mean_turnover": 999.0,
            }
        )
    pd.DataFrame(portfolio_rows).to_csv(
        run_directory / "portfolio_summary.csv", index=False
    )
    for artifact in REQUIRED_ARTIFACTS:
        path = run_directory / artifact
        if path.exists():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == ".png":
            path.write_bytes(b"complete-test-figure")
        else:
            path.write_text("complete test artifact\n", encoding="utf-8")
    return run_directory


def _record_worker(
    data_root: str,
    run_directory: str,
    start_event,
    result_queue,
) -> None:
    """Record one run in a real child process and report its public outcome."""
    start_event.wait()
    try:
        record_successful_run(Path(data_root), Path(run_directory))
    except ValueError as error:
        if "duplicate" in str(error).lower():
            result_queue.put("duplicate")
        else:
            result_queue.put(f"value-error:{error}")
    except BaseException as error:
        result_queue.put(f"error:{type(error).__name__}:{error}")
    else:
        result_queue.put("success")


def _run_concurrently(data_root: Path, run_directories: list[Path]) -> list[str]:
    context = multiprocessing.get_context("spawn")
    start_event = context.Event()
    result_queue = context.Queue()
    processes = [
        context.Process(
            target=_record_worker,
            args=(str(data_root), str(run_directory), start_event, result_queue),
        )
        for run_directory in run_directories
    ]
    for process in processes:
        process.start()
    start_event.set()
    for process in processes:
        process.join(timeout=20)
        assert not process.is_alive()
        assert process.exitcode == 0
    return [result_queue.get(timeout=5) for _ in processes]


def test_successful_run_appends_one_scoreboard_row_and_writes_card(tmp_path: Path):
    """Catches a complete immutable run failing to become one local record and card."""
    run_directory = write_complete_run(tmp_path)

    record_successful_run(tmp_path, run_directory)

    scoreboard = load_scoreboard(tmp_path)
    assert scoreboard[["factor_id", "run_id"]].to_dict("records") == [
        {"factor_id": "REV5", "run_id": "run-001"}
    ]
    assert scoreboard.loc[0, "relative_run_path"] == "runs/REV5/run-001"
    assert (tmp_path / "factor_cards" / "REV5.html").is_file()


def test_duplicate_run_id_is_rejected_without_overwrite(tmp_path: Path):
    """Catches duplicate evidence replacing or adding to an immutable record."""
    run_directory = write_complete_run(tmp_path)
    record_successful_run(tmp_path, run_directory)
    original_bytes = (tmp_path / "factor_scoreboard.parquet").read_bytes()

    with pytest.raises(ValueError, match="(?i)duplicate"):
        record_successful_run(tmp_path, run_directory)

    assert len(load_scoreboard(tmp_path)) == 1
    assert (tmp_path / "factor_scoreboard.parquet").read_bytes() == original_bytes


def test_incomplete_run_does_not_change_scoreboard_or_card(tmp_path: Path):
    """Catches partial publication creating any executable performance record."""
    run_directory = write_complete_run(tmp_path, run_id="broken")
    (run_directory / "portfolio_summary.csv").unlink()

    with pytest.raises(FileNotFoundError, match="portfolio_summary.csv"):
        record_successful_run(tmp_path, run_directory)

    assert not (tmp_path / "factor_scoreboard.parquet").exists()
    assert not (tmp_path / "factor_scoreboard.duckdb").exists()
    assert not (tmp_path / "factor_cards").exists()


def test_scoreboard_and_duckdb_contain_only_formal_executable_metrics(tmp_path: Path):
    """Catches diagnostic portfolios or robustness samples entering executable fields."""
    record_successful_run(tmp_path, write_complete_run(tmp_path))

    scoreboard = load_scoreboard(tmp_path)
    row = scoreboard.iloc[0]
    assert row["mean_rank_ic_5d"] == pytest.approx(0.05)
    assert row["tradable_mean_rank_ic_5d"] == pytest.approx(0.06)
    assert row["top_k_gross_sharpe_5d"] == pytest.approx(0.5)
    assert row["top_k_net_sharpe_5d"] == pytest.approx(0.49)
    assert row["top_k_mean_turnover_5d"] == pytest.approx(0.25)
    assert row["portfolio_kind"] == "top_k_long"
    assert row["is_diagnostic"] == False  # noqa: E712
    assert [column for column in scoreboard.columns if "diagnostic" in column] == [
        "is_diagnostic"
    ]
    assert 999.0 not in row.tolist()

    with duckdb.connect(str(tmp_path / "factor_scoreboard.duckdb"), read_only=True) as db:
        mirror = db.execute("SELECT * FROM factor_scoreboard").fetchdf()
    pd.testing.assert_frame_equal(
        mirror.sort_index(axis=1), scoreboard.sort_index(axis=1), check_dtype=False
    )


def test_run_path_must_be_exactly_contained_below_private_runs(tmp_path: Path):
    """Catches arbitrary or symlink-escaped directories being recorded as private runs."""
    data_root = tmp_path / "private"
    data_root.mkdir()
    outside = tmp_path / "outside"
    outside_run = write_complete_run(outside)

    with pytest.raises(ValueError, match="data_root/runs"):
        record_successful_run(data_root, outside_run)

    (data_root / "runs").mkdir()
    (data_root / "runs" / "REV5").symlink_to(
        outside / "runs" / "REV5", target_is_directory=True
    )
    with pytest.raises(ValueError, match="data_root/runs"):
        record_successful_run(data_root, data_root / "runs" / "REV5" / "run-001")
    assert not (data_root / "factor_scoreboard.parquet").exists()


def test_factor_card_uses_latest_created_at_not_append_order(tmp_path: Path):
    """Catches an older late-arriving run replacing the latest successful factor card."""
    latest = write_complete_run(
        tmp_path, run_id="run-latest", created_at="2026-08-14T02:00:00+00:00"
    )
    older = write_complete_run(
        tmp_path, run_id="run-older", created_at="2026-08-14T01:00:00+00:00"
    )

    record_successful_run(tmp_path, latest)
    record_successful_run(tmp_path, older)

    card = (tmp_path / "factor_cards" / "REV5.html").read_text(encoding="utf-8")
    assert "run-latest" in card
    assert "run-older" not in card
    assert "runs/REV5/run-latest" in card
    assert "IC and Rank IC by horizon" in card
    assert "Long-only Top-K metrics" in card


def test_factor_card_uses_latest_formal_run_not_newer_experimental_run(tmp_path: Path):
    """Catches exploratory evidence replacing the latest formal factor card."""
    formal = write_complete_run(
        tmp_path,
        run_id="run-formal",
        created_at="2026-08-14T01:00:00+00:00",
    )
    experimental = write_complete_run(
        tmp_path,
        run_id="run-experimental",
        created_at="2026-08-14T02:00:00+00:00",
        run_type="experimental",
    )

    record_successful_run(tmp_path, formal)
    record_successful_run(tmp_path, experimental)

    scoreboard = load_scoreboard(tmp_path)
    assert scoreboard.set_index("run_id")["run_type"].to_dict() == {
        "run-formal": "formal",
        "run-experimental": "experimental",
    }
    card = (tmp_path / "factor_cards" / "REV5.html").read_text(encoding="utf-8")
    assert "run-formal" in card
    assert "run-experimental" not in card


def test_scoreboard_rejects_unknown_run_type(tmp_path: Path):
    """Catches arbitrary metadata values bypassing formal-card selection rules."""
    run_directory = write_complete_run(tmp_path, run_type="unclassified")

    with pytest.raises(ValueError, match="run_type"):
        record_successful_run(tmp_path, run_directory)

    assert not (tmp_path / "factor_scoreboard.parquet").exists()


def test_failed_generation_activation_keeps_all_three_previous_views(
    tmp_path: Path, monkeypatch
):
    """Catches a mid-publish failure exposing mixed Parquet, DuckDB, and card versions."""
    original = write_complete_run(tmp_path, run_id="run-original")
    record_successful_run(tmp_path, original)
    new_run = write_complete_run(
        tmp_path, run_id="run-new", created_at="2026-08-14T03:00:00+00:00"
    )
    original_parquet = load_scoreboard(tmp_path)[["factor_id", "run_id"]].to_dict(
        "records"
    )
    with duckdb.connect(
        str(tmp_path / "factor_scoreboard.duckdb"), read_only=True
    ) as database:
        original_duckdb = database.execute(
            "SELECT factor_id, run_id FROM factor_scoreboard"
        ).fetchall()
    original_card = (tmp_path / "factor_cards" / "REV5.html").read_text(
        encoding="utf-8"
    )

    def fail_activation(*args, **kwargs):
        raise OSError("injected generation activation failure")

    monkeypatch.setattr(
        records_module, "_activate_generation", fail_activation, raising=False
    )
    with pytest.raises(OSError, match="injected generation activation failure"):
        record_successful_run(tmp_path, new_run)

    assert load_scoreboard(tmp_path)[["factor_id", "run_id"]].to_dict(
        "records"
    ) == original_parquet
    with duckdb.connect(
        str(tmp_path / "factor_scoreboard.duckdb"), read_only=True
    ) as database:
        assert database.execute(
            "SELECT factor_id, run_id FROM factor_scoreboard"
        ).fetchall() == original_duckdb
    assert (
        tmp_path / "factor_cards" / "REV5.html"
    ).read_text(encoding="utf-8") == original_card


def test_concurrent_duplicate_record_has_one_success_and_one_row(tmp_path: Path):
    """Catches concurrent duplicate writers both passing the append-only check."""
    run_directory = write_complete_run(tmp_path)

    outcomes = _run_concurrently(tmp_path, [run_directory] * 4)

    assert sorted(outcomes) == ["duplicate", "duplicate", "duplicate", "success"]
    assert load_scoreboard(tmp_path)[["factor_id", "run_id"]].to_dict("records") == [
        {"factor_id": "REV5", "run_id": "run-001"}
    ]


def test_concurrent_distinct_records_are_never_lost(tmp_path: Path):
    """Catches concurrent valid appends replacing rather than extending one another."""
    run_directories = [
        write_complete_run(tmp_path, run_id=f"run-{number:03d}")
        for number in range(6)
    ]

    outcomes = _run_concurrently(tmp_path, run_directories)

    assert outcomes.count("success") == len(run_directories)
    assert sorted(load_scoreboard(tmp_path)["run_id"].tolist()) == [
        f"run-{number:03d}" for number in range(6)
    ]


def test_complete_production_artifact_manifest_is_mandatory(tmp_path: Path):
    """Catches absent or subset manifests being accepted as complete production runs."""
    run_directory = write_complete_run(tmp_path)
    summary_path = run_directory / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["artifacts"] = list(REQUIRED_ARTIFACTS[:-1])
    summary_path.write_text(json.dumps(summary), encoding="utf-8")

    with pytest.raises(ValueError, match="REQUIRED_ARTIFACTS"):
        record_successful_run(tmp_path, run_directory)

    assert not (tmp_path / "factor_scoreboard.parquet").exists()


def test_symlinked_runs_root_is_rejected_before_any_artifact_is_opened(tmp_path: Path):
    """Catches an external runs-root symlink being trusted as private evidence."""
    outside = tmp_path / "outside"
    run_directory = write_complete_run(outside)
    (run_directory / "summary.json").write_text("{invalid", encoding="utf-8")
    data_root = tmp_path / "private"
    data_root.mkdir()
    (data_root / "runs").symlink_to(outside / "runs", target_is_directory=True)

    with pytest.raises(ValueError, match="runs root"):
        record_successful_run(
            data_root, data_root / "runs" / "REV5" / "run-001"
        )

    assert not (data_root / "factor_scoreboard.parquet").exists()


def test_factor_card_breaks_created_at_ties_by_stable_run_id(tmp_path: Path):
    """Catches equal timestamps making the latest card depend on append order."""
    created_at = "2026-08-14T02:00:00+00:00"
    lower = write_complete_run(tmp_path, run_id="run-aaa", created_at=created_at)
    higher = write_complete_run(tmp_path, run_id="run-zzz", created_at=created_at)

    record_successful_run(tmp_path, lower)
    record_successful_run(tmp_path, higher)

    card = (tmp_path / "factor_cards" / "REV5.html").read_text(encoding="utf-8")
    assert "run-zzz" in card
    assert "run-aaa" not in card
