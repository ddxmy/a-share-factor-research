"""Mining State: persistent storage for MiningState and Factor Library (L).

MiningState tracks saturation per success pattern:
  - factor_count: number of factors belonging to this pattern
  - recent_success_rate: success rate in the last iteration
  - avg_correlation: average pairwise Spearman |corr| among the pattern's factors

Saturation score = weighted combination of the three metrics (higher = more saturated).
Patterns exceeding saturation threshold are moved to forbidden_regions automatically.
"""

import json
import os
import dataclasses
import typing

import utils.config


@dataclasses.dataclass
class PatternState:
    """Mining state for a single success pattern — tracks saturation."""
    factor_count: int = 0
    recent_success_rate: float = 0.0  # 0.0–1.0, success rate in last iteration
    avg_correlation: float = 0.0      # 0.0–1.0, mean pairwise |corr| among factors

    # Saturation weights (sum to 1.0)
    W_COUNT = 0.3
    W_SUCCESS = 0.3
    W_CORR = 0.4

    # Normalisation: factor_count saturates at ~10 factors
    COUNT_CAP = 10

    def saturation_score(self) -> float:
        """Compute saturation score in [0, 1]. Higher = more saturated."""
        s_count = min(self.factor_count / self.COUNT_CAP, 1.0)
        # Low recent success rate → high saturation (pattern is exhausted)
        s_success = 1.0 - self.recent_success_rate
        s_corr = self.avg_correlation
        return (self.W_COUNT * s_count +
                self.W_SUCCESS * s_success +
                self.W_CORR * s_corr)

    def to_dict(self) -> dict:
        return {
            "factor_count": self.factor_count,
            "recent_success_rate": round(self.recent_success_rate, 4),
            "avg_correlation": round(self.avg_correlation, 4),
            "saturation_score": round(self.saturation_score(), 4),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PatternState":
        return cls(
            factor_count=data.get("factor_count", 0),
            recent_success_rate=data.get("recent_success_rate", 0.0),
            avg_correlation=data.get("avg_correlation", 0.0),
        )


@dataclasses.dataclass
class FactorRecord:
    """A single factor formula stored in the library."""
    factor_id: int = 0         # auto-increment ID (1, 2, 3, ...)
    factor_name: str = ""      # human-readable name
    formula: str = ""
    tot_score: float = 0.0

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: typing.Dict[str, typing.Any]) -> "FactorRecord":
        # Backward compat: old "score" key → "tot_score"
        if "tot_score" not in data and "score" in data:
            data = {**data, "tot_score": data["score"]}
        # Backward compat: old hash-based factor_id (str) → move to factor_name
        if isinstance(data.get("factor_id"), str):
            old_hash = data["factor_id"]
            data = {**data, "factor_name": data.get("factor_name", old_hash), "factor_id": 0}
        return cls(**{k: v for k, v in data.items() if k in {"factor_id", "factor_name", "formula", "tot_score"}})


@dataclasses.dataclass
class Pattern:
    """A distilled pattern (success or forbidden) stored in Experience Memory.

    Attributes:
        pattern:   High-level logical concept name (e.g. "HigherMomentRegimes"),
                   used for SUCCESS patterns only.
        description: Natural language explanation of the financial logic,
                     used for SUCCESS patterns only.
        direction: Terse label telling the generator which research direction to AVOID
                   (e.g. "VWAP Deviation variants"), used for FORBIDDEN regions only.
        category: "success" or "forbidden".
        mining_state: MiningState for SUCCESS patterns — tracks saturation.
    """
    pattern: str = ""         # success: concept name
    description: str = ""     # success: financial logic
    direction: str = ""       # forbidden: which direction to avoid
    category: str = "success"  # "success" or "forbidden"
    mining_state: PatternState = dataclasses.field(default_factory=PatternState)

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        d = dataclasses.asdict(self)
        # Remove empty string fields
        for key in list(d.keys()):
            if isinstance(d[key], str) and not d[key]:
                del d[key]
        # Remove category field (redundant)
        d.pop("category", None)
        # For forbidden regions, remove description and mining_state
        if "direction" in d:
            d.pop("description", None)
            d.pop("mining_state", None)
        return d

    @classmethod
    def from_dict(cls, data: typing.Dict[str, typing.Any]) -> "Pattern":
        ms = data.get("mining_state", {})
        mining_state = PatternState.from_dict(ms) if isinstance(ms, dict) else PatternState()
        defaults = {
            "pattern": data.get("pattern", ""),
            "description": data.get("description", ""),
            "direction": data.get("direction", ""),
            "category": data.get("category", "success"),
            "mining_state": mining_state,
        }
        return cls(**defaults)


class FactorLibrary:
    """Factor Library L: holds all historically admitted (good) factors."""

    def __init__(self, filepath: str = utils.config.FACTOR_LIBRARY_FILE):
        self.filepath = filepath
        self.factors: typing.List[FactorRecord] = []
        self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.factors = [FactorRecord.from_dict(d) for d in data]

    def save(self):
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump([f.to_dict() for f in self.factors], f, indent=2, ensure_ascii=False)

    def _next_id(self) -> int:
        if not self.factors:
            return 1
        return max(f.factor_id for f in self.factors) + 1

    def add(self, record: FactorRecord):
        if not record.factor_id:
            record.factor_id = self._next_id()
        self.factors.append(record)
        self.save()

    def get_records(self) -> typing.List[FactorRecord]:
        return self.factors[:]

    def remove_by_id(self, factor_id: int) -> bool:
        """Remove a factor by its factor_id. Returns True if removed."""
        before = len(self.factors)
        self.factors = [f for f in self.factors if f.factor_id != factor_id]
        if len(self.factors) < before:
            self.save()
            return True
        return False

    def clear(self):
        self.factors = []
        self.save()


class ExperienceMemory:
    """Experience Memory M: holds success patterns (P_succ) and forbidden regions (禁区).

    Memory evolves through Formation (F) and Evolution (E) operators.

    MiningState Integration:
      - Each success pattern carries a PatternState tracking saturation.
      - Patterns exceeding saturation threshold can be auto-moved to forbidden_regions.
    """

    SATURATION_THRESHOLD = 0.7  # patterns above this are candidates for forbidden

    def __init__(self, filepath: str = utils.config.MEMORY_FILE):
        self.filepath = filepath
        self.success_patterns: typing.List[Pattern] = []
        self.forbidden_regions: typing.List[Pattern] = []
        self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.success_patterns = [
                    Pattern.from_dict(d) for d in data.get("success_patterns", [])
                ]
                self.forbidden_regions = [
                    Pattern.from_dict(d) for d in data.get("forbidden_regions", [])
                ]

    def save(self):
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        payload = {
            "success_patterns": [p.to_dict() for p in self.success_patterns],
            "forbidden_regions": [p.to_dict() for p in self.forbidden_regions],
        }
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    def replace_success_patterns(self, patterns: typing.List[Pattern]):
        self.success_patterns = patterns
        self.save()

    def update_pattern_state(
        self,
        pattern_name: str,
        factor_count: int,
        recent_success_rate: float,
        avg_correlation: float,
    ) -> bool:
        """Update the MiningState of a success pattern by name.

        Returns True if the pattern was found and updated.
        """
        for p in self.success_patterns:
            if p.pattern == pattern_name:
                p.mining_state = PatternState(
                    factor_count=factor_count,
                    recent_success_rate=recent_success_rate,
                    avg_correlation=avg_correlation,
                )
                self.save()
                return True
        return False

    def evolve_saturated_patterns(self) -> typing.List[str]:
        """Move success patterns exceeding SATURATION_THRESHOLD to forbidden_regions.

        Returns the names of patterns moved.
        """
        moved = []
        remaining = []
        for p in self.success_patterns:
            if p.mining_state.saturation_score() >= self.SATURATION_THRESHOLD:
                # Move to forbidden
                forbidden = Pattern(
                    direction=p.pattern,
                )
                self.forbidden_regions.append(forbidden)
                moved.append(p.pattern)
            else:
                remaining.append(p)

        if moved:
            self.success_patterns = remaining
            self.save()

        return moved

    def clear(self):
        self.success_patterns = []
        self.forbidden_regions = []
        self.save()
