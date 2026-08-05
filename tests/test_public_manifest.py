import subprocess
import sys
from pathlib import Path

from tools.validate_public_manifest import validate_public_tree


def test_public_tree_rejects_data_and_local_paths(tmp_path):
    (tmp_path / "alpha158" / "data.parquet").parent.mkdir()
    (tmp_path / "alpha158" / "data.parquet").write_bytes(b"x")
    (tmp_path / "README.md").write_text(
        "/" + "Users/alice/private.duckdb", encoding="utf-8"
    )

    violations = validate_public_tree(tmp_path, {"README.md", "alpha158/"})

    assert any("data.parquet" in item for item in violations)
    assert any("absolute local path" in item for item in violations)


def test_public_tree_allows_only_report_figure_pngs(tmp_path):
    figure = tmp_path / "alpha158" / "reports" / "figures" / "equity.png"
    figure.parent.mkdir(parents=True)
    figure.write_bytes(b"png")
    (tmp_path / "README.md").write_text("Public overview", encoding="utf-8")

    violations = validate_public_tree(tmp_path, {"README.md", "alpha158/"})

    assert violations == []


def test_public_tree_rejects_secret_and_env_filename(tmp_path):
    (tmp_path / ".env").write_text("FM_API_KEY" + "=secret", encoding="utf-8")

    violations = validate_public_tree(tmp_path, {".env"})

    assert any("disallowed .env filename" in item for item in violations)
    assert any("FM_API_KEY" in item for item in violations)


def test_public_tree_rejects_allowlisted_readme_symlink(tmp_path):
    (tmp_path / "README.md").symlink_to(
        Path("/") / "Users" / "alice" / "private.md"
    )

    violations = validate_public_tree(tmp_path, {"README.md"})

    assert any("README.md" in item and "symbolic link" in item for item in violations)


def test_public_tree_rejects_symlinked_root_before_resolving(tmp_path):
    clean_root = tmp_path / "clean"
    clean_root.mkdir()
    linked_root = tmp_path / "public"
    linked_root.symlink_to(clean_root, target_is_directory=True)

    violations = validate_public_tree(linked_root, set())

    assert any("root symbolic link" in item for item in violations)


def test_command_exits_nonzero_for_manifest_violation(tmp_path):
    (tmp_path / "alpha158").mkdir()
    (tmp_path / "alpha158" / "private.db").write_bytes(b"x")
    validator = Path(__file__).parents[1] / "tools" / "validate_public_manifest.py"

    result = subprocess.run(
        [sys.executable, str(validator), str(tmp_path), "--allow", "alpha158/"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "private.db" in result.stdout


def test_command_reads_allowlist_file_and_allows_its_parent_directory(tmp_path):
    (tmp_path / "alpha158").mkdir()
    (tmp_path / "alpha158" / "README.md").write_text("Public experiment", encoding="utf-8")
    allowlist = tmp_path.parent / "public_allowlist.txt"
    allowlist.write_text("# curated paths\nalpha158/README.md\n", encoding="utf-8")
    validator = Path(__file__).parents[1] / "tools" / "validate_public_manifest.py"

    result = subprocess.run(
        [
            sys.executable,
            str(validator),
            str(tmp_path),
            "--allowlist",
            str(allowlist),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "passed" in result.stdout
