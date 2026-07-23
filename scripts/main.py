"""Factor evaluation CLI - evaluates factor formulas using run_factor + FactorTest.

Usage:
    # Evaluate one or more factor formulas
    python main.py eval "Cs_Rank(Ts_Mean(close, 20))" "Ts_Std(volume, 10)"

    # Print operator library
    python main.py operators

    # Read experience memory (with MiningState)
    python main.py memory-read

    # Read factor library
    python main.py library-read

    # Update memory with new patterns
    python main.py memory-update --success '{"pattern":"ConceptName","description":"..."}'

    # Update mining state for existing patterns
    python main.py memory-update --update-state '{"pattern":"Name","factor_count":3,"recent_success_rate":0.5,"avg_correlation":0.42}'

    # Evolve saturated patterns to forbidden regions
    python main.py memory-update --evolve

    # Add factor to library
    python main.py library-add "formula" 45.2

    # Remove factor from library
    python main.py library-remove <factor_id>

    # Reset memory and library
    python main.py reset
"""

import argparse
import datetime
import json
import os
import re
import shutil

import evaluation.evaluator
import memory.mining_state
import operators.operator_library
import utils.config


def _safe_identifier(value):
    """Convert a user-facing factor name to a valid Python identifier fragment."""
    identifier = re.sub(r"\W+", "_", value.strip())
    identifier = re.sub(r"_+", "_", identifier).strip("_")
    if not identifier:
        identifier = "generated_factor"
    if identifier[0].isdigit():
        identifier = f"f_{identifier}"
    return identifier


def _current_version():
    return "V" + datetime.date.today().strftime("%Y%m%d")


def _factor_artifact_stem(record):
    return f"factor_{record.factor_id}_{_safe_identifier(record.factor_name)}"


def _factor_script_path(record):
    return os.path.join(
        utils.config.FACTOR_SCRIPT_DIR,
        _current_version(),
        f"{_factor_artifact_stem(record)}.py",
    )


def _factor_tmp_data_dir(record):
    return os.path.join(
        utils.config.TMP_DATA_DIR,
        f"{_current_version()}_{_factor_artifact_stem(record)}",
    )


def _write_factor_script(record):
    """Persist an admitted formula as a runnable europa-style factor script."""
    path = _factor_script_path(record)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    factor_name_literal = repr(record.factor_name)
    formula_literal = repr(record.formula)
    function_name = f"factor_{record.factor_id}_{_safe_identifier(record.factor_name)}"
    script = f'''"""Generated factor script for admitted factor #{record.factor_id}.

Formula:
    {record.formula}
"""
import os
import sys

import numpy as np
import pandas as pd


FACTOR_NAME = {factor_name_literal}
FACTOR_TYPE = "T-1_factor"
FORMULA = {formula_literal}


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)


def {function_name}(start_date, end_date, md_data_file, return_fillna_dic=False):
    """Compute this generated formula factor in europa T-1 factor format."""
    if return_fillna_dic:
        return {{FACTOR_NAME: np.nan, "data": ["MD"]}}

    from evaluation.evaluator import FormulaExecutor
    from marketdata import get_tradingday

    lookback_start = int(get_tradingday(
        None, start_date=20120101, end_date=start_date, shift=-260,
    )[0])
    executor = FormulaExecutor(
        md_data_file=md_data_file,
        start_date=lookback_start,
        end_date=end_date,
    )
    panel = executor.compute(FORMULA)
    stacked = panel.stack()
    stacked.name = FACTOR_NAME
    stacked.index.names = ["dt", "Ticker"]
    return pd.DataFrame(stacked)


if __name__ == "__main__":
    start_date, end_date = 20160101, 20161231
    md_data_file = "/workspace/public/data/project/other_data/MD_data/md_20120101_20250706.pq"
    factor_df = {function_name}(start_date, end_date, md_data_file)
    print(factor_df.groupby(level=0).count().head())
'''
    with open(path, "w", encoding="utf-8") as f:
        f.write(script)
    return path


def _remove_factor_scripts(factor_id):
    """Move generated scripts for a removed factor to factor_script/_retired/ instead of deleting."""
    if not os.path.isdir(utils.config.FACTOR_SCRIPT_DIR):
        return []
    retired_dir = os.path.join(utils.config.FACTOR_SCRIPT_DIR, "_retired")
    os.makedirs(retired_dir, exist_ok=True)
    moved = []
    prefix = f"factor_{factor_id}_"
    for root, _, filenames in os.walk(utils.config.FACTOR_SCRIPT_DIR):
        # Skip the _retired directory itself to avoid re-moving
        if os.path.basename(root) == "_retired" or "/_retired" in root:
            continue
        for filename in filenames:
            if filename.startswith(prefix) and filename.endswith(".py"):
                src = os.path.join(root, filename)
                dst = os.path.join(retired_dir, filename)
                shutil.move(src, dst)
                moved.append(src)
    return moved


def cmd_eval(args):
    """Evaluate one or more factor formulas with correlation check and auto-admission."""
    # 1. Score evaluation (via run_factor + FactorTest subprocess)
    candidates = []
    for idx, formula in enumerate(args.formulas):
        try:
            score = evaluation.evaluator.tot_score_evaluation(formula)
            verdict = "PASS" if score >= args.threshold else "FAIL"
            candidates.append({
                "factor_id": idx,
                "formula": formula,
                "tot_score": score,
                "verdict": verdict
            })
        except Exception as e:
            candidates.append({
                "factor_id": idx,
                "formula": formula,
                "error": str(e),
                "verdict": "ERROR"
            })

    # 2. Correlation check against existing library (report-only, no admission)
    library = memory.mining_state.FactorLibrary()
    results = evaluation.evaluator.check_correlation_admission(
        candidates, library, corr_threshold=args.corr_threshold, admit=False
    )

    # 3. Intra-batch dedup (report-only, no admission)
    results = evaluation.evaluator.intra_batch_dedup(
        results, library, corr_threshold=args.corr_threshold, admit=False
    )

    # Output as JSON
    print(json.dumps(results, indent=2, ensure_ascii=False))


def cmd_operators(args):
    """Print the operator library."""
    lib = operators.operator_library.OPERATOR_LIBRARY
    print(lib.format_for_llm())


def cmd_memory_read(args):
    """Read experience memory (success patterns with MiningState + forbidden regions)."""
    mem = memory.mining_state.ExperienceMemory()
    data = {
        "success_patterns": [p.to_dict() for p in mem.success_patterns],
        "forbidden_regions": [p.to_dict() for p in mem.forbidden_regions]
    }
    print(json.dumps(data, indent=2, ensure_ascii=False))


def cmd_library_read(args):
    """Read factor library."""
    lib = memory.mining_state.FactorLibrary()
    data = [rec.to_dict() for rec in lib.get_records()]
    print(json.dumps(data, indent=2, ensure_ascii=False))


def cmd_memory_update(args):
    """Update experience memory with new patterns or update existing pattern states."""
    mem = memory.mining_state.ExperienceMemory()

    # Add new success patterns (with optional initial mining state)
    if args.success:
        success_data = json.loads(args.success)
        if not isinstance(success_data, list):
            success_data = [success_data]

        new_patterns = []
        for item in success_data:
            ms_data = item.get("mining_state", {})
            mining_state = memory.mining_state.PatternState(
                factor_count=ms_data.get("factor_count", 0),
                recent_success_rate=ms_data.get("recent_success_rate", 0.0),
                avg_correlation=ms_data.get("avg_correlation", 0.0),
            )
            pattern = memory.mining_state.Pattern(
                pattern=item.get("pattern", ""),
                description=item.get("description", ""),
                category="success",
                mining_state=mining_state
            )
            new_patterns.append(pattern)

        # Merge with existing
        existing = mem.success_patterns
        mem.replace_success_patterns(existing + new_patterns)

    # Update mining state for existing patterns
    if args.update_state:
        state_data = json.loads(args.update_state)
        if not isinstance(state_data, list):
            state_data = [state_data]

        updated = []
        for item in state_data:
            pattern_name = item.get("pattern", "")
            updated_flag = mem.update_pattern_state(
                pattern_name=pattern_name,
                factor_count=item.get("factor_count", 0),
                recent_success_rate=item.get("recent_success_rate", 0.0),
                avg_correlation=item.get("avg_correlation", 0.0),
            )
            if updated_flag:
                updated.append(pattern_name)

        if updated:
            print(f"Updated mining state for: {', '.join(updated)}")

    # Run evolution: move saturated patterns to forbidden regions
    if args.evolve:
        moved = mem.evolve_saturated_patterns()
        if moved:
            print(f"Moved saturated patterns to forbidden: {', '.join(moved)}")
        else:
            print("No patterns exceeded saturation threshold")

    print("Memory updated successfully")


def cmd_library_add(args):
    """Add a factor to the library."""
    lib = memory.mining_state.FactorLibrary()

    record = memory.mining_state.FactorRecord(
        factor_name=args.factor_name,
        formula=args.formula,
        tot_score=args.score
    )

    lib.add(record)
    script_path = _write_factor_script(record)
    tmp_data_dir = _factor_tmp_data_dir(record)
    evaluation.evaluator.tot_score_evaluation(record.formula, result_dir=tmp_data_dir)
    print(f"Added factor: id={record.factor_id}, name={args.factor_name} (score: {args.score})")
    print(f"Saved factor script: {script_path}")
    print(f"Saved evaluation artifacts: {tmp_data_dir}")


def cmd_library_remove(args):
    """Remove a factor from the library by ID."""
    lib = memory.mining_state.FactorLibrary()

    removed = lib.remove_by_id(args.factor_id)
    if removed:
        removed_scripts = _remove_factor_scripts(args.factor_id)
        print(f"Removed factor: id={args.factor_id}")
        if removed_scripts:
            print(f"Removed factor scripts: {', '.join(removed_scripts)}")
    else:
        print(f"Factor not found: id={args.factor_id}")


def cmd_reset(args):
    """Reset memory and library."""
    mem = memory.mining_state.ExperienceMemory()
    lib = memory.mining_state.FactorLibrary()

    mem.clear()
    lib.clear()

    print("Memory and library cleared")


def main():
    parser = argparse.ArgumentParser(
        description="FactorMiner CLI - Factor evaluation and management"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # eval command
    eval_parser = subparsers.add_parser("eval", help="Evaluate factor formulas")
    eval_parser.add_argument("formulas", nargs="+", help="Factor formulas to evaluate")
    eval_parser.add_argument("--threshold", type=float, default=30.0,
                            help="Pass threshold (default: 30.0)")
    eval_parser.add_argument("--corr-threshold", type=float, default=0.5,
                            help="Spearman correlation threshold for redundancy check (default: 0.5)")

    # operators command
    subparsers.add_parser("operators", help="Print operator library")

    # memory-read command
    subparsers.add_parser("memory-read", help="Read experience memory with MiningState")

    # library-read command
    subparsers.add_parser("library-read", help="Read factor library")

    # memory-update command
    mem_update_parser = subparsers.add_parser("memory-update", help="Update experience memory")
    mem_update_parser.add_argument("--success", type=str,
                                   help="Add new success patterns (JSON with optional mining_state)")
    mem_update_parser.add_argument("--update-state", type=str,
                                   help="Update mining state for existing patterns (JSON)")
    mem_update_parser.add_argument("--evolve", action="store_true",
                                   help="Move saturated patterns to forbidden regions")

    # library-add command
    lib_add_parser = subparsers.add_parser("library-add", help="Add factor to library")
    lib_add_parser.add_argument("factor_name", type=str, help="Human-readable factor name (economic concept, e.g. Trend_Reliability_Switch_V2)")
    lib_add_parser.add_argument("formula", help="Factor formula")
    lib_add_parser.add_argument("score", type=float, help="tot_score")

    # library-remove command
    lib_remove_parser = subparsers.add_parser("library-remove", help="Remove factor from library")
    lib_remove_parser.add_argument("factor_id", type=int, help="Factor ID to remove")

    # reset command
    subparsers.add_parser("reset", help="Reset memory and library")

    args = parser.parse_args()

    if args.command == "eval":
        cmd_eval(args)
    elif args.command == "operators":
        cmd_operators(args)
    elif args.command == "memory-read":
        cmd_memory_read(args)
    elif args.command == "library-read":
        cmd_library_read(args)
    elif args.command == "memory-update":
        cmd_memory_update(args)
    elif args.command == "library-add":
        cmd_library_add(args)
    elif args.command == "library-remove":
        cmd_library_remove(args)
    elif args.command == "reset":
        cmd_reset(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
