"""Point-in-time CSI 300 membership reconstruction.

The monthly index-weight records are observations of index membership, not
effective-date events. This module converts adjacent snapshot differences into
dated adjustment events and then into left-closed, right-open membership
intervals.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd


@dataclass(frozen=True)
class MembershipEvent:
    """A dated, balanced index membership adjustment."""

    event_id: str
    event_type: str
    effective_date: pd.Timestamp
    previous_snapshot: pd.Timestamp
    snapshot_date: pd.Timestamp
    added: tuple[str, ...]
    removed: tuple[str, ...]
    evidence: str

    def as_record(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "effective_date": self.effective_date,
            "previous_snapshot": self.previous_snapshot,
            "snapshot_date": self.snapshot_date,
            "added_count": len(self.added),
            "removed_count": len(self.removed),
            "added": ", ".join(self.added),
            "removed": ", ".join(self.removed),
            "evidence": self.evidence,
        }


def _normalize_date(value: Any) -> pd.Timestamp:
    return pd.Timestamp(value).normalize()


def _second_friday(year: int, month: int) -> pd.Timestamp:
    first_day = pd.Timestamp(year=year, month=month, day=1)
    days_until_friday = (4 - first_day.weekday()) % 7
    first_friday = first_day + pd.Timedelta(days=days_until_friday)
    return first_friday + pd.Timedelta(days=7)


def next_open_date(day: Any, open_dates: Sequence[Any]) -> pd.Timestamp:
    """Return the first exchange trading date strictly after *day*."""

    normalized_open_dates = pd.DatetimeIndex(open_dates).normalize().sort_values().unique()
    position = normalized_open_dates.searchsorted(_normalize_date(day), side="right")
    if position >= len(normalized_open_dates):
        raise ValueError(f"No exchange trading date exists after {day}")
    return pd.Timestamp(normalized_open_dates[position])


def regular_effective_date(
    year: int,
    month: int,
    open_dates: Sequence[Any],
) -> pd.Timestamp:
    """Compute the CSI regular adjustment date for June or December."""

    if month not in {6, 12}:
        raise ValueError(f"Regular CSI 300 month must be June or December, got {month}")
    return next_open_date(_second_friday(year, month), open_dates)


def snapshot_changes(membership: pd.DataFrame) -> pd.DataFrame:
    """Compute balanced membership deltas between adjacent monthly snapshots."""

    required = {"snapshot_date", "con_code"}
    missing = required - set(membership.columns)
    if missing:
        raise ValueError(f"Membership data is missing columns: {sorted(missing)}")

    normalized = membership.loc[:, ["snapshot_date", "con_code"]].copy()
    normalized["snapshot_date"] = pd.to_datetime(normalized["snapshot_date"]).dt.normalize()
    if normalized.duplicated(["snapshot_date", "con_code"]).any():
        raise ValueError("Duplicate (snapshot_date, con_code) membership keys")

    member_sets = (
        normalized.groupby("snapshot_date")["con_code"]
        .apply(lambda values: set(values.astype(str)))
        .sort_index()
    )
    records: list[dict[str, Any]] = []
    previous_date: pd.Timestamp | None = None
    previous_members: set[str] | None = None
    for snapshot_date, current_members in member_sets.items():
        if previous_members is not None:
            records.append(
                {
                    "previous_snapshot": pd.Timestamp(previous_date),
                    "snapshot_date": pd.Timestamp(snapshot_date),
                    "added": tuple(sorted(current_members - previous_members)),
                    "removed": tuple(sorted(previous_members - current_members)),
                }
            )
        previous_date = pd.Timestamp(snapshot_date)
        previous_members = current_members

    changes = pd.DataFrame(records)
    changes["added_count"] = changes["added"].str.len()
    changes["removed_count"] = changes["removed"].str.len()
    return changes


def build_adjustment_events(
    membership: pd.DataFrame,
    open_dates: Sequence[Any],
    temporary_adjustments: Iterable[Mapping[str, Any]],
    *,
    start_year: int,
    end_year: int,
) -> list[MembershipEvent]:
    """Map observed snapshot deltas to official regular or temporary dates."""

    changes = snapshot_changes(membership)
    changes = changes.loc[
        (changes["added_count"] > 0) | (changes["removed_count"] > 0)
    ].copy()
    changes = changes.loc[
        changes["snapshot_date"].dt.year.between(start_year, end_year)
    ].copy()

    temporary_by_delta: dict[
        tuple[frozenset[str], frozenset[str]], Mapping[str, Any]
    ] = {}
    for adjustment in temporary_adjustments:
        key = (
            frozenset(adjustment["added"]),
            frozenset(adjustment["removed"]),
        )
        if key in temporary_by_delta:
            raise ValueError(f"Duplicate temporary-adjustment delta: {key}")
        temporary_by_delta[key] = adjustment

    events: list[MembershipEvent] = []
    matched_temporary_ids: set[str] = set()
    for row in changes.itertuples(index=False):
        added = tuple(row.added)
        removed = tuple(row.removed)
        delta_key = (frozenset(added), frozenset(removed))
        snapshot_month = pd.Timestamp(row.snapshot_date).month

        if delta_key in temporary_by_delta:
            adjustment = temporary_by_delta[delta_key]
            event_id = str(adjustment["event_id"])
            matched_temporary_ids.add(event_id)
            event = MembershipEvent(
                event_id=event_id,
                event_type="temporary",
                effective_date=_normalize_date(adjustment["effective_date"]),
                previous_snapshot=_normalize_date(row.previous_snapshot),
                snapshot_date=_normalize_date(row.snapshot_date),
                added=added,
                removed=removed,
                evidence="official event date + frozen monthly snapshot delta",
            )
        elif snapshot_month in {6, 12}:
            snapshot_year = pd.Timestamp(row.snapshot_date).year
            event = MembershipEvent(
                event_id=f"REG_{snapshot_year}_{snapshot_month:02d}",
                event_type="regular",
                effective_date=regular_effective_date(
                    snapshot_year,
                    snapshot_month,
                    open_dates,
                ),
                previous_snapshot=_normalize_date(row.previous_snapshot),
                snapshot_date=_normalize_date(row.snapshot_date),
                added=added,
                removed=removed,
                evidence="CSI methodology rule + frozen monthly snapshot delta",
            )
        else:
            raise ValueError(
                "Observed non-regular snapshot change has no verified temporary event: "
                f"{row.previous_snapshot} -> {row.snapshot_date}, "
                f"added={added}, removed={removed}"
            )

        if len(event.added) != len(event.removed):
            raise ValueError(f"Unbalanced index event: {event.event_id}")
        if not event.previous_snapshot < event.effective_date <= event.snapshot_date:
            raise ValueError(
                f"Effective date is outside its snapshot evidence window: {event.event_id}"
            )
        events.append(event)

    expected_temporary_ids = {
        str(adjustment["event_id"]) for adjustment in temporary_adjustments
    }
    if matched_temporary_ids != expected_temporary_ids:
        raise ValueError(
            "Temporary event ledger does not match snapshot deltas: "
            f"matched={sorted(matched_temporary_ids)}, "
            f"expected={sorted(expected_temporary_ids)}"
        )

    events.sort(key=lambda event: (event.effective_date, event.event_id))
    effective_dates = [event.effective_date for event in events]
    if len(effective_dates) != len(set(effective_dates)):
        raise ValueError("Multiple membership events share an effective date")
    return events


def build_membership_intervals(
    baseline_members: Iterable[str],
    events: Sequence[MembershipEvent],
    *,
    interval_start: Any,
    interval_end_exclusive: Any,
    expected_constituents: int = 300,
) -> pd.DataFrame:
    """Create left-closed, right-open point-in-time membership intervals."""

    start = _normalize_date(interval_start)
    end = _normalize_date(interval_end_exclusive)
    if not start < end:
        raise ValueError("interval_start must precede interval_end_exclusive")

    active = set(map(str, baseline_members))
    if len(active) != expected_constituents:
        raise ValueError(
            f"Baseline has {len(active)} members; expected {expected_constituents}"
        )

    opened: dict[str, tuple[pd.Timestamp, str]] = {
        code: (start, "BASELINE_2015_01") for code in active
    }
    interval_records: list[dict[str, Any]] = []

    for event in events:
        if not start < event.effective_date < end:
            raise ValueError(f"Event outside requested interval: {event.event_id}")

        removed = set(event.removed)
        added = set(event.added)
        missing_removals = removed - active
        duplicate_additions = added & active
        if missing_removals:
            raise ValueError(
                f"{event.event_id} removes inactive members: {sorted(missing_removals)}"
            )
        if duplicate_additions:
            raise ValueError(
                f"{event.event_id} adds active members: {sorted(duplicate_additions)}"
            )

        for code in sorted(removed):
            member_start, entry_event_id = opened.pop(code)
            interval_records.append(
                {
                    "index_code": "000300.SH",
                    "con_code": code,
                    "effective_start": member_start,
                    "effective_end_exclusive": event.effective_date,
                    "entry_event_id": entry_event_id,
                    "exit_event_id": event.event_id,
                }
            )
        active.difference_update(removed)

        for code in sorted(added):
            opened[code] = (event.effective_date, event.event_id)
        active.update(added)

        if len(active) != expected_constituents:
            raise ValueError(
                f"{event.event_id} leaves {len(active)} constituents; "
                f"expected {expected_constituents}"
            )

    for code in sorted(active):
        member_start, entry_event_id = opened[code]
        interval_records.append(
            {
                "index_code": "000300.SH",
                "con_code": code,
                "effective_start": member_start,
                "effective_end_exclusive": end,
                "entry_event_id": entry_event_id,
                "exit_event_id": "FORMAL_SAMPLE_END",
            }
        )

    intervals = pd.DataFrame(interval_records).sort_values(
        ["con_code", "effective_start"]
    ).reset_index(drop=True)
    invalid_intervals = (
        intervals["effective_start"] >= intervals["effective_end_exclusive"]
    )
    if invalid_intervals.any():
        raise ValueError("Membership interval has non-positive duration")

    overlaps = (
        intervals.sort_values(["con_code", "effective_start"])
        .assign(
            previous_end=lambda frame: frame.groupby("con_code")[
                "effective_end_exclusive"
            ].shift()
        )
        .eval("effective_start < previous_end")
        .fillna(False)
    )
    if overlaps.any():
        raise ValueError("Overlapping membership intervals detected")
    return intervals


def membership_on_dates(
    intervals: pd.DataFrame,
    dates: Iterable[Any],
    *,
    date_column: str,
) -> pd.DataFrame:
    """Expand compact intervals at requested observation dates only."""

    observation_dates = pd.DataFrame(
        {date_column: pd.DatetimeIndex(dates).normalize().unique()}
    )
    expanded = observation_dates.merge(intervals, how="cross")
    expanded = expanded.loc[
        (expanded[date_column] >= expanded["effective_start"])
        & (expanded[date_column] < expanded["effective_end_exclusive"])
    ].copy()
    expanded = expanded.sort_values([date_column, "con_code"]).reset_index(drop=True)
    return expanded


def reconcile_snapshot_sets(
    intervals: pd.DataFrame,
    membership: pd.DataFrame,
    *,
    end_date: Any,
) -> pd.DataFrame:
    """Compare reconstructed membership against every observed month-end snapshot."""

    observed = membership.loc[:, ["snapshot_date", "con_code"]].copy()
    observed["snapshot_date"] = pd.to_datetime(observed["snapshot_date"]).dt.normalize()
    observed = observed.loc[observed["snapshot_date"] <= _normalize_date(end_date)]
    snapshot_dates = sorted(observed["snapshot_date"].unique())
    reconstructed = membership_on_dates(
        intervals,
        snapshot_dates,
        date_column="snapshot_date",
    )

    observed_sets = observed.groupby("snapshot_date")["con_code"].apply(set)
    reconstructed_sets = reconstructed.groupby("snapshot_date")["con_code"].apply(set)
    records: list[dict[str, Any]] = []
    for snapshot_date in snapshot_dates:
        observed_members = observed_sets.loc[snapshot_date]
        reconstructed_members = reconstructed_sets.loc[snapshot_date]
        records.append(
            {
                "snapshot_date": pd.Timestamp(snapshot_date),
                "observed_count": len(observed_members),
                "reconstructed_count": len(reconstructed_members),
                "missing_from_reconstruction": ", ".join(
                    sorted(observed_members - reconstructed_members)
                ),
                "unexpected_in_reconstruction": ", ".join(
                    sorted(reconstructed_members - observed_members)
                ),
                "exact_match": observed_members == reconstructed_members,
            }
        )
    return pd.DataFrame(records)
