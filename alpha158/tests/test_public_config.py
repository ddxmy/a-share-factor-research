from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR / "src"))

from alpha158_research.public_config import require_data_root  # noqa: E402


def test_public_configuration_rejects_a_missing_data_root(monkeypatch):
    monkeypatch.delenv("A_SHARE_DATA_ROOT", raising=False)

    with pytest.raises(RuntimeError, match="A_SHARE_DATA_ROOT must be set"):
        require_data_root()


def test_public_configuration_rejects_a_nonexistent_data_root(monkeypatch, tmp_path):
    monkeypatch.setenv("A_SHARE_DATA_ROOT", str(tmp_path / "not-present"))

    with pytest.raises(FileNotFoundError, match="does not name an existing directory"):
        require_data_root()


def test_ridge_runner_rejects_a_missing_data_root_before_model_execution():
    environment = os.environ.copy()
    environment.pop("A_SHARE_DATA_ROOT", None)
    runner = PROJECT_DIR / "scripts" / "run_ridge.py"

    result = subprocess.run(
        [sys.executable, str(runner), "--dry-run"],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert result.returncode != 0
    assert "A_SHARE_DATA_ROOT must be set" in result.stderr
