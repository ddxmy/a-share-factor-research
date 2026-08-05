"""Public configuration boundary for private Alpha158 research inputs."""

from __future__ import annotations

import os
from pathlib import Path


DATA_ROOT_ENVIRONMENT_VARIABLE = "A_SHARE_DATA_ROOT"


def require_data_root() -> Path:
    """Return the researcher-supplied data root or fail before model work begins."""

    value = os.environ.get(DATA_ROOT_ENVIRONMENT_VARIABLE)
    if not value:
        raise RuntimeError(
            "A_SHARE_DATA_ROOT must be set to a private research-data directory "
            "before loading inputs or executing a model."
        )
    root = Path(value).expanduser()
    if not root.is_dir():
        raise FileNotFoundError(
            f"A_SHARE_DATA_ROOT does not name an existing directory: {root}"
        )
    return root.resolve()
