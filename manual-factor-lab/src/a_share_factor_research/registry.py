"""Read the frozen factor registry and bind entries to researcher functions."""

from dataclasses import dataclass
import importlib
from pathlib import Path
import re
from typing import Callable

import pandas as pd

RawFactorCallable = Callable[[pd.DataFrame], pd.DataFrame]
REGISTRY_PATH = Path(__file__).resolve().parents[2] / "factor_registry.csv"


@dataclass(frozen=True)
class FactorDefinition:
    """A single, pre-registered factor and its researcher-owned calculation."""

    factor_id: str
    formula_definition: str
    required_daily_fields: tuple[str, ...]
    signal_availability: str
    economic_hypothesis: str
    pre_registered_direction: str
    status: str
    compute: RawFactorCallable


def resolve_factor_callable(factor_id: str) -> RawFactorCallable:
    """Import and validate the dedicated researcher callable for one factor."""
    module_name = f"factor_modules.{factor_id.lower()}"
    module = importlib.import_module(module_name)
    module_factor_id = getattr(module, "FACTOR_ID", None)
    if module_factor_id != factor_id:
        raise ValueError(
            f"Factor module {module_name!r} identifier {module_factor_id!r} "
            f"does not match requested factor {factor_id!r}."
        )

    compute = getattr(module, "compute", None)
    if not callable(compute):
        raise ValueError(f"Factor module {module_name!r} has no callable 'compute'.")
    return compute


def load_factor_definition(factor_id: str) -> FactorDefinition:
    """Load exactly one registry entry and its matching researcher callable."""
    registry = pd.read_csv(REGISTRY_PATH)
    rows = registry.loc[registry["factor_id"] == factor_id]
    if len(rows) != 1:
        raise ValueError(f"Expected exactly one registry entry for {factor_id!r}; found {len(rows)}.")

    row = rows.iloc[0]
    direction = row["pre_registered_direction"]
    if direction not in {"positive", "negative"}:
        raise ValueError(f"Factor {factor_id!r} has an invalid direction: {direction!r}.")

    compute = resolve_factor_callable(factor_id)

    required_daily_fields = tuple(
        field.strip() for field in str(row["required_daily_fields"]).split(";") if field.strip()
    )
    return FactorDefinition(
        factor_id=factor_id,
        formula_definition=row["formula_definition"],
        required_daily_fields=required_daily_fields,
        signal_availability=row["signal_availability"],
        economic_hypothesis=row["economic_hypothesis"],
        pre_registered_direction=direction,
        status=row["status"],
        compute=compute,
    )


def compute_raw_factor(factor_id: str, panel: pd.DataFrame) -> pd.DataFrame:
    """Run a registered researcher calculation without transforming its raw values."""
    raw_values = load_factor_definition(factor_id).compute(panel)
    if not isinstance(raw_values, pd.DataFrame):
        raise TypeError(f"Factor {factor_id!r} must return a long-form DataFrame.")

    required_columns = {"trade_date", "security_id", "raw_value"}
    missing_columns = required_columns.difference(raw_values.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Factor {factor_id!r} output is missing required columns: {missing}.")
    return raw_values


def required_history_sessions(definition: FactorDefinition) -> int:
    """Return the explicit trailing-session requirement encoded in the registry formula."""
    formula = definition.formula_definition.lower()
    matches = [
        int(value)
        for value in re.findall(
            r"(?:t-|trailing[- ]|rolling_(?:low|high)_|over trailing[- ])(\d+)", formula
        )
    ]
    return max(matches, default=0)
