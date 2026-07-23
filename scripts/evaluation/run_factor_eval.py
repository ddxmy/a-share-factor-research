#!/usr/bin/env python3
"""Standalone factor evaluation via run_factor + FactorTest (Python 3.8).

Called as a subprocess from factor-miner (Python 3.12).
Takes a factor definition on stdin as JSON, writes results to stdout as JSON,
and saves a detailed report file.

Input JSON:
{
  "formula": "...",
  "factor_name": "...",
  "factor_type": "T-1_factor",
  "start_date": 20160101,
  "end_date": 20181231,
  "basic_file_path": "/workspace/.../20160101_20181231.pq",
  "result_dir": "./results",
  "output_file": "/tmp/factor_eval_result.json"   <-- JSON result written here
}

Output JSON:
{
  "factor_name": "...",
  "formula": "...",
  "tot_score": 55.5,
  "verdict": "PASS" (>=30) or "FAIL" (<30)
}
"""
import json
import os
import sys
import traceback

# Ensure we can import the .so modules and marketdata
# The .so files live in the project root: /workspace/user_homes/xiezutian/factor_mining/
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
# factor-framework (europa) and marketdata
_FACTOR_MINER_DIR = os.path.join(_PROJECT_ROOT, 'factor-miner')
if _FACTOR_MINER_DIR not in sys.path:
    sys.path.insert(0, _FACTOR_MINER_DIR)
# europa __init__ also needs /workspace/public/factor_mining
_PUB_MD = '/workspace/public/factor_mining'
if os.path.isdir(os.path.join(_PUB_MD, 'marketdata')) and _PUB_MD not in sys.path:
    sys.path.insert(0, _PUB_MD)

import pandas as pd


def main():
    input_data = json.load(sys.stdin)

    formula = input_data["formula"]
    factor_name = input_data["factor_name"]
    factor_type = input_data.get("factor_type", "T-1_factor")
    start_date = input_data.get("start_date", 20160101)
    end_date = input_data.get("end_date", 20181231)
    basic_file_path = input_data.get(
        "basic_file_path",
        "/workspace/public/data/project/basic_data/20160101_20181231.pq",
    )
    result_dir = input_data.get("result_dir", "./results")
    output_file = input_data.get("output_file", "")

    # ----- Create a dynamic factor function -----
    # This wraps the factor-miner's FormulaExecutor evaluation into a proper
    # factor function compatible with run_factor's interface.
    # We import FormulaExecutor here to compute the factor panel.

    # Add factor-miner scripts to path for FormulaExecutor
    _scripts_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    if _scripts_dir not in sys.path:
        sys.path.insert(0, _scripts_dir)

    # Create a factor function that uses FormulaExecutor under the hood.
    # run_factor.so calls this twice:
    #   1. return_fillna_dic=False → compute & return factor panel
    #   2. return_fillna_dic=True  → return {factor_name: <median>} for NaN fill
    _fill_value: dict = {}  # {factor_name: fill_value}, populated on first call

    def dynamic_factor(start_date, end_date, md_data_file, return_fillna_dic=False):
        if return_fillna_dic:
            # run_factor.so's internal processing left some NaNs — fill with median
            fill_val = _fill_value.get(factor_name, 0.0)
            return {factor_name: fill_val, 'data': ['MD']}

        from evaluation.evaluator import FormulaExecutor
        # Align data-load range with hand-written factors: shift back from
        # evaluation start_date far enough to cover any rolling window (~252
        # trading days ≈ 1 calendar year).  This keeps unstack column sets and
        # rolling-window boundaries consistent with europa factor conventions.
        from marketdata import get_tradingday
        _lookback_start = int(get_tradingday(
            None, start_date=20120101, end_date=start_date, shift=-260,
        )[0])
        executor = FormulaExecutor(
            md_data_file=md_data_file,
            start_date=_lookback_start,
            end_date=end_date,
        )
        panel = executor.compute(formula)

        # Compute median while still in panel form, before stacking
        _fill_value[factor_name] = float(panel.median().median())

        # Convert panel DataFrame (date × Ticker) to stacked format (dt, Ticker)
        stacked = panel.stack()
        stacked.name = factor_name
        stacked.index.names = ['dt', 'Ticker']
        factor_df = pd.DataFrame(stacked)

        # Return all dates — run_factor.so needs dates before start_date
        # for T-1 shift, and will crop to the evaluation window itself.
        return factor_df

    # ----- Run through run_factor -----
    from run_factor import run_factor
    from test_factor_demo import strongFactorTest as FactorTest

    factor_df2, fill_dic = run_factor(
        dynamic_factor, factor_name, factor_type,
        start_date, end_date, basic_file_path, result_dir,
        interval_res=False, n_jobs=4,
    )

    # ----- Run FactorTest -----
    factor_test = FactorTest(start_date, end_date, cal_mi=False)
    check_score_res, factor_corr = factor_test.factor_test(
        factor_df2,
        result_path=result_dir,
        factor_corr_test=False,
        generate_pdf=False,
    )

    # ----- Extract tot_score -----
    try:
        tot_obj = check_score_res.get("tot_score", pd.Series())
        if isinstance(tot_obj, pd.Series):
            tot_score_val = float(tot_obj.get("score", tot_obj.get(factor_name, 0.0)))
        else:
            tot_score_val = float(tot_obj.loc["score", tot_obj.columns[0]])
        if pd.isna(tot_score_val):
            tot_score_val = 0.0
    except (KeyError, ValueError, TypeError, IndexError):
        tot_score_val = 0.0

    threshold = 30.0
    verdict = "PASS" if tot_score_val >= threshold else "FAIL"

    # ----- Output -----
    report = {
        "factor_name": factor_name,
        "formula": formula,
        "tot_score": tot_score_val,
        "verdict": verdict,
    }

    report_json = json.dumps(report, indent=2, ensure_ascii=False, default=str)

    if output_file:
        os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report_json)
    else:
        print(report_json)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        result = {
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "tot_score": 0.0,
            "verdict": "ERROR",
        }
        print(json.dumps(result, ensure_ascii=False, default=str))
        sys.exit(1)
