"""Validate that a repository tree is safe to publish."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Iterable


DISALLOWED_EXTENSIONS = {
    ".duckdb",
    ".db",
    ".parquet",
    ".pq",
    ".ipynb",
    ".log",
    ".so",
}
DISALLOWED_DIRECTORIES = {
    ".claude",
    ".superpowers",
    ".codex_backup",
    "data",
    "factor_script",
    "factor_framework",
}
_LOCAL_ABSOLUTE_PREFIX = "/" + "Users/"
_OPENAI_SECRET_PREFIX = "s" + "k-"
_TUSHARE_ASSIGNMENT = "TUSHARE_TOKEN" + "="
_FM_API_KEY_ASSIGNMENT = "FM_API_KEY" + "="
CONTENT_PATTERNS = {
    _LOCAL_ABSOLUTE_PREFIX: "absolute local path",
    _OPENAI_SECRET_PREFIX: f"credential pattern {_OPENAI_SECRET_PREFIX!r}",
    _TUSHARE_ASSIGNMENT: f"credential pattern {_TUSHARE_ASSIGNMENT!r}",
    _FM_API_KEY_ASSIGNMENT: f"credential pattern {_FM_API_KEY_ASSIGNMENT!r}",
}
DEFAULT_ALLOWLIST = {
    ".gitignore",
    "README.md",
    "LICENSE",
    "requirements.txt",
    "migration/public_allowlist.txt",
    "alpha158/",
    "tests/",
    "tools/",
}
_IGNORED_RUNTIME_DIRECTORIES = {".git", ".pytest_cache", "__pycache__"}


def _normalize_allowlist(allowlist: Iterable[str]) -> set[str]:
    normalized: set[str] = set()
    for entry in allowlist:
        entry = entry.replace("\\", "/")
        normalized.add(entry[2:] if entry.startswith("./") else entry)
    return normalized


def _is_allowlisted(relative_path: Path, allowlist: set[str]) -> bool:
    relative = relative_path.as_posix()
    if relative in allowlist:
        return True
    # An exact allowlisted file also permits walking through its parent directory
    # without granting permission to unrelated sibling files.
    if any(entry.startswith(f"{relative}/") for entry in allowlist):
        return True
    return any(
        entry.endswith("/")
        and (relative == entry.rstrip("/") or relative.startswith(entry))
        for entry in allowlist
    )


def _is_env_filename(path: Path) -> bool:
    name = path.name.lower()
    return name == ".env" or name.startswith(".env.") or name.endswith(".env")


def _is_allowed_png(relative_path: Path) -> bool:
    parts = relative_path.parts
    return len(parts) >= 4 and parts[:3] == ("alpha158", "reports", "figures")


def _read_content_violations(path: Path, relative_path: Path) -> list[str]:
    try:
        contents = path.read_bytes().decode("utf-8", errors="ignore")
    except OSError as error:
        return [f"{relative_path.as_posix()}: cannot read file ({error})"]

    return [
        f"{relative_path.as_posix()}: {description}"
        for pattern, description in CONTENT_PATTERNS.items()
        if pattern in contents
    ]


def validate_public_tree(root: Path, allowlist: set[str]) -> list[str]:
    """Return all violations found under *root* against the public manifest."""
    root = Path(root)
    if root.is_symlink():
        return [f"{root}: root symbolic link is not allowed"]
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"public tree root is not a directory: {root}")

    normalized_allowlist = _normalize_allowlist(allowlist)
    violations: list[str] = []

    for directory, directory_names, file_names in os.walk(root, topdown=True):
        directory_path = Path(directory)
        for name in directory_names[:]:
            if name in _IGNORED_RUNTIME_DIRECTORIES:
                directory_names.remove(name)
                continue

            child = directory_path / name
            relative_child = child.relative_to(root)
            if child.is_symlink():
                violations.append(f"{relative_child.as_posix()}/: symbolic link is not allowed")
                directory_names.remove(name)
            elif name in DISALLOWED_DIRECTORIES:
                violations.append(f"{relative_child.as_posix()}/: disallowed directory")
                directory_names.remove(name)
            elif not _is_allowlisted(relative_child, normalized_allowlist):
                violations.append(f"{relative_child.as_posix()}/: disallowed path")
                directory_names.remove(name)

        for name in file_names:
            if name == ".git":
                continue

            child = directory_path / name
            relative_child = child.relative_to(root)
            suffix = child.suffix.lower()

            if child.is_symlink():
                violations.append(f"{relative_child.as_posix()}: symbolic link is not allowed")
                continue
            if not _is_allowlisted(relative_child, normalized_allowlist):
                violations.append(f"{relative_child.as_posix()}: disallowed path")

            if _is_env_filename(child):
                violations.append(f"{relative_child.as_posix()}: disallowed .env filename")
            if suffix in DISALLOWED_EXTENSIONS:
                violations.append(f"{relative_child.as_posix()}: disallowed binary data extension")
            if suffix == ".png" and not _is_allowed_png(relative_child):
                violations.append(f"{relative_child.as_posix()}: PNG is only allowed in alpha158/reports/figures/")

            violations.extend(_read_content_violations(child, relative_child))

    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path("."))
    parser.add_argument(
        "--allow",
        action="append",
        dest="allow",
        help="Allow an exact file or a directory prefix ending in '/'. Repeat as needed.",
    )
    parser.add_argument(
        "--allowlist",
        type=Path,
        dest="allowlist_file",
        help="Read allowed paths from a UTF-8 text file; blank lines and # comments are ignored.",
    )
    arguments = parser.parse_args()

    if arguments.allowlist_file and arguments.allow:
        parser.error("--allowlist cannot be combined with --allow")
    if arguments.allowlist_file:
        try:
            allowlist = {
                line.strip()
                for line in arguments.allowlist_file.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.lstrip().startswith("#")
            }
        except OSError as error:
            parser.error(f"cannot read allowlist file: {error}")
    else:
        allowlist = set(arguments.allow) if arguments.allow else DEFAULT_ALLOWLIST
    try:
        violations = validate_public_tree(arguments.root, allowlist)
    except ValueError as error:
        parser.error(str(error))

    if violations:
        print("Public manifest validation failed:")
        print("\n".join(f"- {violation}" for violation in violations))
        return 1

    print("Public manifest validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
