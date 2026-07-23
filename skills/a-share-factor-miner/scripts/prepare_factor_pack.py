#!/usr/bin/env python3
"""Materialize and statically lint one already-sealed Factor Pack-40."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SKILL_ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_NAMES = {
    "next_open_to_close",
    "next_close_to_close",
    "primary_label_available",
    "execution_date",
    "future_return",
    "label",
}
ALLOWED_FIELDS = {
    "open", "close", "high", "low", "pre_close", "vwap", "volume", "amt",
    "pct_chg", "Returns", "change", "turn", "total_shares", "free_float_shares",
    "adjfactor", "mkt_cap_ard", "pe", "pe_ttm", "pb", "ps", "ps_ttm",
    "dv_ratio", "dv_ttm",
}
VALUATION_FIELDS = {"pe", "pe_ttm", "pb", "ps", "ps_ttm", "dv_ratio", "dv_ttm"}
ALLOWED_CALLS = {
    "Ts_Rank", "Ts_Delay", "Ts_Delta", "Ts_Return", "Ts_Sum", "Ts_Mean",
    "Ts_Std", "Ts_Var", "Ts_Max", "Ts_Min", "Ts_Skewness", "Ts_Kurtosis",
    "Ts_ZScore", "Ts_Correlation", "Ts_Covariance", "Ts_Rsquare", "Ts_Beta",
    "Ts_Residual", "Ts_WMA", "Ts_EMA", "Ts_Median", "Ts_MAD", "Ts_Quantile",
    "Ts_CountNans", "Ts_ArgMax", "Ts_ArgMin", "Ts_DecayLinear", "Ts_DecayExp",
    "Cs_Rank", "Cs_ZScore", "Cs_Mean", "Cs_Std", "Cs_Sum", "Cs_Median",
    "Cs_MAD", "Cs_Percentile", "Cs_Neutralize", "Cs_Winsorize", "Add", "Sub",
    "Mul", "Div", "Abs", "Sign", "Log", "Sqrt", "Exp", "Power", "SignedPower",
    "Max", "Min", "Inverse", "Neg", "Clip", "If", "Greater", "Less", "Equal",
    "And", "Or", "Not", "MACD", "RSI", "BBands_Upper", "BBands_Lower",
    "VWAP_Deviation", "Price_Momentum", "Slope", "Volatility_Ratio", "Trend_Strength",
}
CROSS_SECTION_SCALAR_CALLS = {"Cs_Mean", "Cs_Std", "Cs_Sum", "Cs_Median", "Cs_MAD"}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_formula(formula: str) -> str:
    tree = ast.parse(formula, mode="eval")
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Cs_Percentile":
            node.func.id = "Cs_Rank"
    return ast.dump(tree, annotate_fields=False, include_attributes=False)


def constants_from_script(path: Path) -> dict[str, Any]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    values: dict[str, Any] = {}
    for node in tree.body:
        if not (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        ):
            continue
        try:
            values[node.targets[0].id] = ast.literal_eval(node.value)
        except Exception:
            continue
    return values


def historical_canonicals(target_dir: Path) -> set[str]:
    values: set[str] = set()
    for path in (PROJECT_ROOT / "factor_script").rglob("*.py"):
        if target_dir in path.parents:
            continue
        formula = constants_from_script(path).get("FORMULA")
        if isinstance(formula, str):
            try:
                values.add(canonical_formula(formula))
            except SyntaxError:
                pass
    controls = json.loads(
        (SKILL_ROOT / "references" / "calibration_controls_v1.json").read_text(encoding="utf-8")
    )
    for record in controls["formula_controls"]:
        values.add(canonical_formula(record["formula"]))
    return values


def expression_is_panel(node: ast.AST) -> bool:
    """Conservatively infer whether an expression produces a date-security panel."""
    if isinstance(node, ast.Name):
        return node.id in ALLOWED_FIELDS
    if isinstance(node, ast.Constant):
        return False
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            return False
        if node.func.id == "If":
            return len(node.args) >= 2 and expression_is_panel(node.args[1])
        return any(expression_is_panel(argument) for argument in node.args)
    if isinstance(node, ast.UnaryOp):
        return expression_is_panel(node.operand)
    if isinstance(node, ast.BinOp):
        return expression_is_panel(node.left) or expression_is_panel(node.right)
    if isinstance(node, ast.Compare):
        return expression_is_panel(node.left) or any(
            expression_is_panel(comparator) for comparator in node.comparators
        )
    return False


def lint_formula(record: dict[str, Any], historical: set[str], seen: set[str], enabled_domains: set[str], families: set[str]) -> tuple[str, list[str]]:
    formula = str(record["formula"])
    errors: list[str] = []
    canonical = ""
    if record["data_domain"] not in enabled_domains:
        errors.append("data_domain_not_enabled")
    if record["economic_family"] not in families:
        errors.append("economic_family_not_registered")
    if not isinstance(record.get("target_patterns"), list) or not record["target_patterns"]:
        errors.append("target_patterns_missing")
    try:
        tree = ast.parse(formula, mode="eval")
        canonical = canonical_formula(formula)
        names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        if names & FORBIDDEN_NAMES:
            errors.append("future_or_label_field")
        unknown = names - ALLOWED_FIELDS - ALLOWED_CALLS
        if unknown:
            errors.append("unknown_names:" + ",".join(sorted(unknown)))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Attribute, ast.Subscript, ast.Lambda, ast.ListComp, ast.DictComp)):
                errors.append("forbidden_python_construct")
            if isinstance(node, ast.Call) and (
                not isinstance(node.func, ast.Name) or node.func.id not in ALLOWED_CALLS
            ):
                errors.append("unknown_operator")
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "If"
                and (len(node.args) < 2 or not expression_is_panel(node.args[1]))
            ):
                errors.append("if_true_branch_must_be_panel")
        if not expression_is_panel(tree.body):
            errors.append("scalar_output")
        if (
            isinstance(tree.body, ast.Call)
            and isinstance(tree.body.func, ast.Name)
            and tree.body.func.id in CROSS_SECTION_SCALAR_CALLS
        ):
            errors.append("cross_section_scalar_output")
        if canonical in historical:
            errors.append("historical_or_control_duplicate")
        if canonical in seen:
            errors.append("within_pack_duplicate")
        if record["data_domain"] == "valuation_dividend" and not (names & VALUATION_FIELDS):
            errors.append("valuation_domain_without_valuation_field")
        seen.add(canonical)
    except (SyntaxError, ValueError) as exc:
        errors.append("parse_error:" + str(exc))
    return canonical, sorted(set(errors))


def script_text(record: dict[str, Any], campaign_version: str, pack_number: int) -> str:
    return (
        f'"""Sealed candidate from {campaign_version}, Pack {pack_number:02d}."""\n\n'
        f"CAMPAIGN_VERSION = {campaign_version!r}\n"
        f"PACK_NUMBER = {pack_number}\n"
        f"CANDIDATE_ID = {record['candidate_id']!r}\n"
        f"FACTOR_NAME = {record['factor_name']!r}\n"
        f"FORMULA = {record['formula']!r}\n"
        f"ECONOMIC_HYPOTHESIS = {record['economic_hypothesis']!r}\n"
        f"ECONOMIC_FAMILY = {record['economic_family']!r}\n"
        f"DATA_DOMAIN = {record['data_domain']!r}\n"
        f"TARGET_PATTERNS = {record['target_patterns']!r}\n"
        f"INTERNAL_SUB_BATCH = {int(record['internal_sub_batch'])}\n"
    )


def write_exclusive_or_verify(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != content:
            raise FileExistsError(f"Existing candidate script differs: {path}")
        return
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(content)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack-manifest", required=True)
    parser.add_argument("--script-version", required=True)
    parser.add_argument("--lint-output", required=True)
    args = parser.parse_args()

    pack_path = Path(args.pack_manifest).resolve()
    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    if pack.get("status") != "sealed_before_discovery" or pack.get("visibility") != "discovery_only":
        raise RuntimeError("Factor scripts may be prepared only from a sealed discovery-only pack")
    for path_key, hash_key in (
        ("pack_preparer_path", "pack_preparer_sha256"),
        ("discovery_evaluator_path", "discovery_evaluator_sha256"),
    ):
        implementation_path = Path(pack[path_key])
        if sha256_file(implementation_path) != pack[hash_key]:
            raise RuntimeError(f"Sealed pack implementation changed: {path_key}")
    proposals_path = Path(pack["proposals_path"])
    if sha256_file(proposals_path) != pack["proposals_sha256"]:
        raise RuntimeError("Proposal file changed after pack seal")
    proposals_payload = json.loads(proposals_path.read_text(encoding="utf-8"))
    proposals = proposals_payload.get("proposals", proposals_payload)
    if len(proposals) != 40:
        raise RuntimeError("Expected exactly 40 sealed proposals")

    domains = json.loads((SKILL_ROOT / "references" / "data_domains_v1.json").read_text(encoding="utf-8"))
    enabled_domains = {
        record["domain"]
        for record in domains["domains"]
        if record["status"] == "enabled"
    }
    campaign_path = Path(args.pack_manifest).resolve().parents[1] / "campaign_manifest.json"
    campaign = json.loads(campaign_path.read_text(encoding="utf-8"))
    families = set(campaign["economic_families"])
    target_dir = PROJECT_ROOT / "factor_script" / args.script_version
    historical = historical_canonicals(target_dir)
    seen: set[str] = set()
    lint_rows: list[dict[str, Any]] = []
    for record in proposals:
        canonical, errors = lint_formula(record, historical, seen, enabled_domains, families)
        formula = str(record["formula"])
        expected_hash = pack["candidate_formula_hashes"][record["candidate_id"]]
        actual_hash = hashlib.sha256(formula.encode("utf-8")).hexdigest()
        if actual_hash != expected_hash:
            errors.append("formula_hash_changed_after_seal")
        script_path = target_dir / f"{record['candidate_id']}.py"
        write_exclusive_or_verify(
            script_path,
            script_text(record, pack["campaign_version"], int(pack["pack_number"])),
        )
        lint_rows.append(
            {
                "candidate_id": record["candidate_id"],
                "factor_name": record["factor_name"],
                "formula": formula,
                "formula_hash": actual_hash,
                "canonical_hash": hashlib.sha256(canonical.encode()).hexdigest() if canonical else "",
                "script_path": str(script_path.relative_to(PROJECT_ROOT)),
                "status": "invalid" if errors else "valid",
                "errors": ",".join(sorted(set(errors))),
            }
        )
    lint = pd.DataFrame(lint_rows)
    lint_path = Path(args.lint_output).resolve()
    lint_path.parent.mkdir(parents=True, exist_ok=True)
    lint.to_csv(lint_path, index=False, mode="x")
    print(
        json.dumps(
            {
                "candidate_count": len(lint),
                "valid_count": int(lint["status"].eq("valid").sum()),
                "invalid_count": int(lint["status"].ne("valid").sum()),
                "lint_output": str(lint_path),
                "script_directory": str(target_dir),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
