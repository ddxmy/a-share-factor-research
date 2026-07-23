"""Evaluator: tot_score-based evaluation for candidate alpha factors.

Evaluation:
    Runs each factor through run_factor + FactorTest (Python 3.8 subprocess).
    tot_score = value(50) + mixed(50), each sub-score = discrimination(30) + stability(20).
    Passing: tot_score >= 30.0

Each factor writes a detailed report file to the result directory.

FormulaExecutor is kept here for use by run_factor_eval.py (py38 subprocess).
"""
import hashlib
import json
import logging
import shutil
import tempfile
import os
import re
import subprocess
import typing

import numpy as np
import pandas as pd

import memory.mining_state

logger = logging.getLogger(__name__)

DEFAULT_MD_FILE = "/workspace/public/data/project/other_data/MD_data/md_20120101_20250706.pq"

# ---------------------------------------------------------------------------
# Market-data cache (for FormulaExecutor, used by py38 subprocess)
# ---------------------------------------------------------------------------
_MD_CACHE: dict = {}


def _load_market_data(
    md_data_file: str,
    start_date: int = 20120101,
    end_date: int = 20250706,
) -> dict:
    """Load market data, apply adjfactor + 注册制修正, build panel DataFrames.

    Follows the same preprocessing pattern as factor_t1_example.py:
      1. Read parquet with date filters (start_date ≤ dt ≤ end_date)
      2. Multiply ohlcv/vwap/pre_close by adjfactor (复权)
      3. Re-scale ChiNext (300-xxx ≥ 20200824) & STAR (688-xxx) prices:
         ±20% limit bands → unified ±10% scale (注册制修正)

    Returns a dict with:
        panels: {col_name: DataFrame(date × Ticker)}
    """
    cache_key = (md_data_file, start_date, end_date)
    if cache_key not in _MD_CACHE:
        logger.info(
            "Loading market data from %s [%d – %d] ...",
            md_data_file, start_date, end_date,
        )
        # A local parquet may store ``dt``/``Ticker`` either as ordinary
        # columns or as a persisted MultiIndex.  Prefer predicate pushdown,
        # then fall back to an in-memory filter for index-backed files.
        date_filters = [
            ("dt", ">=", pd.to_datetime(str(start_date))),
            ("dt", "<=", pd.to_datetime(str(end_date))),
        ]
        try:
            md_data = pd.read_parquet(md_data_file, filters=date_filters)
        except (KeyError, ValueError, TypeError):
            md_data = pd.read_parquet(md_data_file)

        if not {"dt", "Ticker"}.issubset(md_data.columns):
            md_data = md_data.reset_index()
        missing_index_columns = {"dt", "Ticker"} - set(md_data.columns)
        if missing_index_columns:
            raise ValueError(
                "Market data must contain dt and Ticker as columns or index levels; "
                f"missing {sorted(missing_index_columns)}"
            )
        md_data["dt"] = pd.to_datetime(md_data["dt"])
        md_data = md_data.loc[
            (md_data["dt"] >= pd.to_datetime(str(start_date)))
            & (md_data["dt"] <= pd.to_datetime(str(end_date)))
        ].set_index(["dt", "Ticker"]).sort_index()

        # ---- Apply adjfactor (复权) ----
        # Europa factors multiply prices by adjfactor — consistent with hand-written factors.
        if "adjfactor" in md_data.columns:
            for col in ["open", "close", "high", "low", "vwap", "pre_close"]:
                if col in md_data.columns:
                    md_data[col] = md_data[col] * md_data["adjfactor"]

        # ---- Re-scale prices for ChiNext (300-xxx) & STAR (688-xxx) (注册制修正) ----
        # ChiNext ≥ 2020-08-24 and STAR (688-xxx) have ±20% price limits,
        # rest have ±10%.  Re-scale so pct_chg is consistent across all stocks.
        md_data["_w"] = 1
        is_chinext = (
            (md_data.index.get_level_values("Ticker").str[0] == "3")
            & (md_data.index.get_level_values("dt") >= pd.Timestamp("2020-08-24"))
        )
        is_star = md_data.index.get_level_values("Ticker").str[:2] == "68"
        md_data.loc[is_chinext | is_star, "_w"] = 2

        for c in ["open", "close", "high", "low", "vwap"]:
            if c in md_data.columns and "pre_close" in md_data.columns:
                md_data[c] = (
                    (md_data[c] / md_data["pre_close"] - 1) / md_data["_w"] + 1
                ) * md_data["pre_close"]

        # pct_chg is stored as raw percentage (e.g. 10.0 = +10%).
        # For ChiNext/STAR, divide by 2 to bring ±20% range onto ±10% scale.
        if "pct_chg" in md_data.columns:
            md_data.loc[is_chinext | is_star, "pct_chg"] = (
                md_data.loc[is_chinext | is_star, "pct_chg"] / 2
            )

        md_data.drop(columns=["_w"], inplace=True, errors="ignore")

        # Build panel DataFrames: index=date, columns=Ticker
        panels: dict[str, pd.DataFrame] = {}
        raw_cols = [
            "open", "close", "high", "low", "volume", "amt",
            "vwap", "pre_close", "pct_chg",
            "total_shares", "free_float_shares", "adjfactor",
            "mkt_cap_ard", "turn", "pe", "pe_ttm", "pb", "ps",
            "ps_ttm", "dv_ratio", "dv_ttm",
        ]
        for col in raw_cols:
            if col in md_data.columns:
                panels[col] = md_data[col].unstack()

        close_df = panels["close"]

        _MD_CACHE[cache_key] = {
            "panels": panels,
            "index": close_df.index,
            "columns": close_df.columns,
        }
        logger.info(
            "Market data loaded: %d dates, %d tickers",
            close_df.shape[0],
            close_df.shape[1],
        )
    return _MD_CACHE[cache_key]


# ---------------------------------------------------------------------------
# FormulaExecutor: symbolic formula -> vectorised pandas computation
# Used by run_factor_eval.py (py38 subprocess) to compute factor panels.
# ---------------------------------------------------------------------------
class FormulaExecutor:
    """Execute symbolic factor formulas on panel market data.

    Every operator is mapped to a deterministic pandas/numpy implementation.
    """

    def __init__(
        self,
        md_data_file: str = DEFAULT_MD_FILE,
        start_date: int = 20120101,
        end_date: int = 20250706,
    ):
        self.md = _load_market_data(
            md_data_file, start_date=start_date, end_date=end_date,
        )
        self.panels = self.md["panels"]
        self.columns = self.md["columns"]
        self._build_namespace()

    def _build_namespace(self) -> None:
        p = self.panels
        ns: dict = {"__builtins__": {}}

        # -- Time-Series operators ------------------------------------
        # All rolling operators accept an optional min_periods (default 1).
        # LLM can override min_periods to require more data before computing:
        #   e.g. Ts_Std(close, 20, min_periods=5)
        def Ts_Rank(x: pd.DataFrame, d, min_periods=1):
            return x.rolling(window=int(d), min_periods=int(min_periods)).rank(pct=True)

        def Ts_Delay(x: pd.DataFrame, d):
            return x.shift(int(d))

        def Ts_Delta(x: pd.DataFrame, d):
            return x.diff(int(d))

        def Ts_Return(x: pd.DataFrame, d):
            return x.pct_change(int(d), fill_method=None)

        def Ts_Sum(x: pd.DataFrame, d, min_periods=1):
            return x.rolling(window=int(d), min_periods=int(min_periods)).sum()

        def Ts_Mean(x: pd.DataFrame, d, min_periods=1):
            return x.rolling(window=int(d), min_periods=int(min_periods)).mean()

        def Ts_Std(x: pd.DataFrame, d, min_periods=1):
            return x.rolling(window=int(d), min_periods=int(min_periods)).std()

        def Ts_Var(x: pd.DataFrame, d, min_periods=1):
            return x.rolling(window=int(d), min_periods=int(min_periods)).var()

        def Ts_Max(x: pd.DataFrame, d, min_periods=1):
            return x.rolling(window=int(d), min_periods=int(min_periods)).max()

        def Ts_Min(x: pd.DataFrame, d, min_periods=1):
            return x.rolling(window=int(d), min_periods=int(min_periods)).min()

        def Ts_Skewness(x: pd.DataFrame, d, min_periods=1):
            return x.rolling(window=int(d), min_periods=int(min_periods)).skew()

        def Ts_Kurtosis(x: pd.DataFrame, d, min_periods=1):
            return x.rolling(window=int(d), min_periods=int(min_periods)).kurt()

        def Ts_ZScore(x: pd.DataFrame, d, min_periods=1):
            mu = Ts_Mean(x, d, min_periods=min_periods)
            sigma = Ts_Std(x, d, min_periods=min_periods)
            return (x - mu) / (sigma + 1e-12)

        def Ts_Correlation(x: pd.DataFrame, y: pd.DataFrame, d, min_periods=1):
            return x.rolling(window=int(d), min_periods=int(min_periods)).corr(y)

        def Ts_Covariance(x: pd.DataFrame, y: pd.DataFrame, d, min_periods=1):
            corr = Ts_Correlation(x, y, d, min_periods=min_periods)
            return corr * Ts_Std(x, d, min_periods=min_periods) * Ts_Std(y, d, min_periods=min_periods)

        def Ts_Rsquare(x: pd.DataFrame, y: pd.DataFrame, d, min_periods=1):
            return Ts_Correlation(x, y, d, min_periods=min_periods) ** 2

        def Ts_Beta(x: pd.DataFrame, y: pd.DataFrame, d, min_periods=1):
            cov = Ts_Covariance(x, y, d, min_periods=min_periods)
            var_y = Ts_Var(y, d, min_periods=min_periods)
            return cov / (var_y + 1e-12)

        def Ts_Residual(x: pd.DataFrame, y: pd.DataFrame, d, min_periods=1):
            beta = Ts_Beta(x, y, d, min_periods=min_periods)
            alpha = Ts_Mean(x, d, min_periods=min_periods) - beta * Ts_Mean(y, d, min_periods=min_periods)
            return x - (alpha + beta * y)

        def Ts_WMA(x: pd.DataFrame, d, min_periods=1):
            d_int = int(d)
            weights = np.arange(1, d_int + 1)
            weights = weights / weights.sum()
            return x.rolling(window=d_int, min_periods=int(min_periods)).apply(
                lambda arr: np.dot(arr, weights[-len(arr):]), raw=True)

        def Ts_EMA(x: pd.DataFrame, d, min_periods=1):
            return x.ewm(span=int(d), min_periods=int(min_periods)).mean()

        def Ts_Median(x: pd.DataFrame, d, min_periods=1):
            return x.rolling(window=int(d), min_periods=int(min_periods)).median()

        def Ts_MAD(x: pd.DataFrame, d, min_periods=1):
            med = Ts_Median(x, d, min_periods=min_periods)
            return (x - med).abs().rolling(window=int(d), min_periods=int(min_periods)).mean()

        def Ts_Quantile(x: pd.DataFrame, d, q, min_periods=1):
            return x.rolling(window=int(d), min_periods=int(min_periods)).quantile(float(q))

        def Ts_CountNans(x: pd.DataFrame, d, min_periods=1):
            return x.isna().rolling(window=int(d), min_periods=int(min_periods)).sum()

        def Ts_ArgMax(x: pd.DataFrame, d, min_periods=1):
            def _argmax_since(arr):
                if len(arr) == 0:
                    return np.nan
                return len(arr) - 1 - np.argmax(arr)
            return x.rolling(window=int(d), min_periods=int(min_periods)).apply(_argmax_since, raw=True)

        def Ts_ArgMin(x: pd.DataFrame, d, min_periods=1):
            def _argmin_since(arr):
                if len(arr) == 0:
                    return np.nan
                return len(arr) - 1 - np.argmin(arr)
            return x.rolling(window=int(d), min_periods=int(min_periods)).apply(_argmin_since, raw=True)

        def Ts_DecayLinear(x: pd.DataFrame, d, min_periods=1):
            d_int = int(d)
            weights = np.arange(d_int, 0, -1)
            weights = weights / weights.sum()
            return x.rolling(window=d_int, min_periods=int(min_periods)).apply(
                lambda arr: np.dot(arr, weights[-len(arr):]), raw=True)

        def Ts_DecayExp(x: pd.DataFrame, d, min_periods=1):
            d_int = int(d)
            weights = np.exp(np.linspace(0, -1, d_int))
            weights = weights / weights.sum()
            return x.rolling(window=d_int, min_periods=int(min_periods)).apply(
                lambda arr: np.dot(arr, weights[-len(arr):]), raw=True)

        # -- Cross-Sectional operators --------------------------------
        def Cs_Rank(x: pd.DataFrame):
            return x.rank(axis=1, pct=True)

        def Cs_ZScore(x: pd.DataFrame):
            mu = x.mean(axis=1)
            sigma = x.std(axis=1)
            return x.sub(mu, axis=0).div(sigma + 1e-12, axis=0)

        def Cs_Mean(x: pd.DataFrame):
            return x.mean(axis=1)

        def Cs_Std(x: pd.DataFrame):
            return x.std(axis=1)

        def Cs_Sum(x: pd.DataFrame):
            return x.sum(axis=1)

        def Cs_Median(x: pd.DataFrame):
            return x.median(axis=1)

        def Cs_MAD(x: pd.DataFrame):
            med = x.median(axis=1)
            return x.sub(med, axis=0).abs().mean(axis=1)

        def Cs_Percentile(x: pd.DataFrame):
            return Cs_Rank(x)

        def Cs_Neutralize(x: pd.DataFrame, group=None):
            return x.sub(Cs_Mean(x), axis=0)

        def Cs_Winsorize(x: pd.DataFrame, lower, upper):
            lower_q = x.quantile(float(lower), axis=1)
            upper_q = x.quantile(float(upper), axis=1)
            # Quantiles are indexed by date, so align them to the row axis.
            # ``axis=1`` aligns the date index against ticker columns and turns
            # the whole panel into NaN.
            return x.clip(lower=lower_q, upper=upper_q, axis=0)

        # -- Mathematical operators -----------------------------------
        def Add(x, y):
            return x + y

        def Sub(x, y):
            return x - y

        def Mul(x, y):
            return x * y

        def Div(x, y):
            # Formulas may divide a panel by a scalar constant (e.g. / 2)
            # as well as another panel.
            if np.isscalar(y):
                safe_y = 1e-12 if y == 0 else y
            else:
                safe_y = y.replace(0, np.nan).fillna(1e-12)
            return x / safe_y

        def Abs(x):
            return x.abs() if hasattr(x, "abs") else np.abs(x)

        def Sign(x):
            return np.sign(x)

        def Log(x):
            return np.log(Abs(x) + 1e-12)

        def Sqrt(x):
            return np.sqrt(Abs(x))

        def Exp(x):
            return np.exp(np.clip(x, -50, 50))

        def Power(x, n):
            return x ** float(n)

        def SignedPower(x, n):
            """Sign-preserving power: sign(x) * |x|^n.

            Formula: sign(x) * |x|^n.  Keeps the original direction while
            compressing (<1) or expanding (>1) the magnitude.
            """
            return np.sign(x) * (np.abs(x) ** float(n))

        def Max(x, y):
            return np.maximum(x, y)

        def Min(x, y):
            return np.minimum(x, y)

        def Inverse(x):
            return 1.0 / (x.replace(0, np.nan).fillna(1e-12))

        def Neg(x):
            return -x

        def Clip(x, lower, upper):
            return x.clip(float(lower), float(upper))

        # -- Logical / Conditional operators --------------------------
        def If(condition, x, y):
            return x.where(condition, y)

        def Greater(x, y):
            return x > y

        def Less(x, y):
            return x < y

        def Equal(x, y):
            return x == y

        def And(x, y):
            return x & y

        def Or(x, y):
            return x | y

        def Not(x):
            return ~x

        # -- Statistical / Composite operators ------------------------
        def MACD(x: pd.DataFrame, fast, slow, signal):
            ema_fast = Ts_EMA(x, int(fast))
            ema_slow = Ts_EMA(x, int(slow))
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=int(signal), min_periods=1).mean()
            return macd_line - signal_line

        def RSI(x: pd.DataFrame, d):
            delta = x.diff()
            gain = delta.where(delta > 0, 0.0)
            loss = (-delta).where(delta < 0, 0.0)
            avg_gain = gain.ewm(alpha=1 / int(d), min_periods=1).mean()
            avg_loss = loss.ewm(alpha=1 / int(d), min_periods=1).mean()
            rs = avg_gain / (avg_loss + 1e-12)
            return 100.0 - (100.0 / (1.0 + rs))

        def BBands_Upper(x: pd.DataFrame, d, k):
            return Ts_Mean(x, d) + float(k) * Ts_Std(x, d)

        def BBands_Lower(x: pd.DataFrame, d, k):
            return Ts_Mean(x, d) - float(k) * Ts_Std(x, d)

        def VWAP_Deviation(x: pd.DataFrame):
            return x - p["vwap"]

        def Price_Momentum(d):
            return p["close"].pct_change(int(d))

        def Volatility_Ratio(d_short, d_long):
            return Ts_Std(p["close"], int(d_short)) / (Ts_Std(p["close"], int(d_long)) + 1e-12)

        def Slope(x: pd.DataFrame, d):
            """Rolling linear regression slope of x on time over d periods.

            Formula: β = cov(t, x) / var(t)  where t = [0, 1, ..., d-1].
            Captures the directional trend strength.
            """
            d = int(d)
            # Pre-compute time index statistics for window size d
            t = np.arange(d, dtype=float)
            t_mean = t.mean()
            t_var = t.var()
            if t_var == 0:
                t_var = 1e-12
            return x.rolling(window=d, min_periods=d).apply(
                lambda arr: np.cov(t[-len(arr):], arr)[0, 1] / t_var
                if len(arr) >= 3 else np.nan,
                raw=True,
            )

        def Trend_Strength(x: pd.DataFrame, d):
            return (Ts_EMA(x, d) - Ts_Mean(x, d)).abs()

        # -- Raw financial fields (from md_20120101_20250706.pq) ----
        ns["open"] = p["open"]
        ns["close"] = p["close"]
        ns["high"] = p["high"]
        ns["low"] = p["low"]
        ns["volume"] = p["volume"]
        ns["amt"] = p["amt"]
        ns["vwap"] = p["vwap"]
        ns["pre_close"] = p["pre_close"]
        ns["pct_chg"] = p["pct_chg"]
        ns["total_shares"] = p["total_shares"]
        ns["free_float_shares"] = p["free_float_shares"]
        ns["adjfactor"] = p["adjfactor"]
        ns["turn"] = p["turn"]
        ns["mkt_cap_ard"] = p["mkt_cap_ard"]
        for field in ("pe", "pe_ttm", "pb", "ps", "ps_ttm", "dv_ratio", "dv_ttm"):
            if field in p:
                ns[field] = p[field]

        # Capitalised aliases
        ns["Open"] = p["open"]
        ns["Close"] = p["close"]
        ns["High"] = p["high"]
        ns["Low"] = p["low"]
        ns["Volume"] = p["volume"]
        ns["VWAP"] = p["vwap"]
        ns["PreClose"] = p["pre_close"]
        ns["Pre_Close"] = p["pre_close"]
        ns["Amt"] = p["amt"]
        ns["Pct_Chg"] = p["pct_chg"]

        # Synthetic fields
        ns["Returns"] = p["close"].pct_change(1, fill_method=None)
        # change = 涨跌额 (close - pre_close), computed from adjfactored+corrected prices
        ns["change"] = p["close"] - p["pre_close"]

        # Register all operators
        for name in [
            "Ts_Rank", "Ts_Delay", "Ts_Delta", "Ts_Return", "Ts_Sum",
            "Ts_Mean", "Ts_Std", "Ts_Var", "Ts_Max", "Ts_Min",
            "Ts_Skewness", "Ts_Kurtosis", "Ts_ZScore", "Ts_Correlation",
            "Ts_Covariance", "Ts_Rsquare", "Ts_Beta", "Ts_Residual",
            "Ts_WMA", "Ts_EMA", "Ts_Median", "Ts_MAD", "Ts_Quantile",
            "Ts_CountNans", "Ts_ArgMax", "Ts_ArgMin", "Ts_DecayLinear",
            "Ts_DecayExp",
            "Cs_Rank", "Cs_ZScore", "Cs_Mean", "Cs_Std", "Cs_Sum",
            "Cs_Median", "Cs_MAD", "Cs_Percentile", "Cs_Neutralize", "Cs_Winsorize",
            "Add", "Sub", "Mul", "Div", "Abs", "Sign", "Log", "Sqrt",
            "Exp", "Power", "SignedPower", "Max", "Min", "Inverse", "Neg", "Clip",
            "If", "Greater", "Less", "Equal", "And", "Or", "Not",
            "MACD", "RSI", "BBands_Upper", "BBands_Lower",
            "Slope",
            "VWAP_Deviation", "Price_Momentum", "Volatility_Ratio", "Trend_Strength",
        ]:
            if name in locals():
                ns[name] = locals()[name]

        self.namespace = ns

    def compute(self, formula: str):
        """Evaluate a symbolic formula and return a panel DataFrame.

        Args:
            formula: e.g. "Ts_Mean(Cs_Rank(close), 20)"

        Returns:
            pd.DataFrame with index=date, columns=Ticker.
        """
        try:
            result = eval(formula, {"__builtins__": {}}, self.namespace)
        except Exception as exc:
            logger.error("Formula evaluation failed: %s | Error: %s", formula, exc)
            raise FormulaEvaluationError(formula, exc) from exc

        if isinstance(result, pd.Series):
            result = pd.DataFrame(
                np.tile(result.values[:, None], (1, len(self.columns))),
                index=result.index,
                columns=self.columns,
            )
        if not isinstance(result, pd.DataFrame):
            raise FormulaEvaluationError(
                formula,
                f"Expected DataFrame, got {type(result).__name__}",
            )
        return result


class FormulaEvaluationError(Exception):
    """Raised when a symbolic formula cannot be evaluated."""
    def __init__(self, formula: str, cause):
        self.formula = formula
        self.cause = cause
        super().__init__(f"Failed to evaluate '{formula}': {cause}")


# ---------------------------------------------------------------------------
# tot_score evaluation via run_factor + FactorTest (Python 3.8 subprocess)
# ---------------------------------------------------------------------------
PY38_PYTHON = "/opt/miniforge3/envs/py38/bin/python"
SCORE_EVAL_SCRIPT = os.path.join(os.path.dirname(__file__), "run_factor_eval.py")
TOT_SCORE_THRESHOLD = 30.0



def tot_score_evaluation(
    factor_formula: str,
    start_date: int = 20160101,
    end_date: int = 20181231,
    basic_file_path: str = "/workspace/public/data/project/basic_data/20160101_20181231.pq",
    result_dir: typing.Optional[str] = None,
    py38_path: str = PY38_PYTHON,
    script_path: str = SCORE_EVAL_SCRIPT,
) -> float:
    """Evaluate a factor via run_factor + FactorTest, returning tot_score.

    Spawns a Python 3.8 subprocess that:
      1. Creates a dynamic factor function wrapping FormulaExecutor
      2. Runs it through run_factor + FactorTest
      3. Returns tot_score (0-100) and writes a detailed report file

    Intermediate .pq files from run_factor.so are written to a temp directory
    that is automatically cleaned up after evaluation.

    Returns tot_score (float, 0-100).  Returns 0.0 on error.
    """
    # Use formula hash as internal identifier for subprocess (not user-facing)
    factor_name = hashlib.md5(factor_formula.encode()).hexdigest()[:8]

    # Use a temp dir for run_factor.so intermediate .pq files — cleaned up after.
    _owned_result_dir = result_dir is None
    if _owned_result_dir:
        result_dir = tempfile.mkdtemp(prefix="factor_eval_")
    os.makedirs(result_dir, exist_ok=True)

    # Use a temp file for JSON result — .so modules write to stdout at C level
    # so subprocess stdout is polluted.  Write result to file instead.
    fd, output_file = tempfile.mkstemp(suffix=".json", prefix="factor_eval_")
    os.close(fd)

    payload = {
        "formula": factor_formula,
        "factor_name": factor_name,
        "factor_type": "T-1_factor",
        "start_date": start_date,
        "end_date": end_date,
        "basic_file_path": basic_file_path,
        "result_dir": result_dir,
        "output_file": output_file,
    }

    logger.info("Running factor evaluation: %s", factor_name)

    try:
        _scripts_dir = os.path.dirname(os.path.abspath(script_path))
        _factor_miner_dir = os.path.dirname(_scripts_dir)
        _project_root = os.path.dirname(_factor_miner_dir)
        _pub_md = "/workspace/public/factor_mining"
        _pythonpath = os.pathsep.join(
            p for p in [_scripts_dir, _factor_miner_dir, _project_root, _pub_md]
        ) + os.pathsep + os.environ.get("PYTHONPATH", "")

        proc = subprocess.run(
            [py38_path, script_path],
            input=json.dumps(payload, ensure_ascii=False),
            capture_output=True,
            text=True,
            timeout=600,
            cwd=_project_root,
            env={**os.environ, "PYTHONPATH": _pythonpath},
        )

        if proc.returncode != 0:
            logger.error(
                "Evaluation subprocess failed for '%s' (exit=%d):\nSTDERR: %s",
                factor_formula, proc.returncode, proc.stderr[-2000:],
            )
            return 0.0

        with open(output_file, "r", encoding="utf-8") as f:
            result = json.load(f)

        if "error" in result:
            logger.warning("Evaluation error for '%s': %s", factor_formula, result["error"])
            return 0.0

        tot_score = float(result.get("tot_score", 0.0))
        verdict = result.get("verdict", "FAIL")

        logger.info(
            "Factor '%s' tot_score=%.1f -> %s",
            factor_name, tot_score, verdict,
        )

        return tot_score

    except subprocess.TimeoutExpired:
        logger.error("Evaluation timed out for '%s'", factor_formula)
        return 0.0
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse evaluation result for '%s': %s", factor_formula, exc)
        return 0.0
    except Exception as exc:
        logger.error("Unexpected error evaluating '%s': %s", factor_formula, exc)
        return 0.0
    finally:
        os.unlink(output_file)
        if _owned_result_dir:
            shutil.rmtree(result_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Factor panel computation (for correlation check)
# ---------------------------------------------------------------------------
_executor_cache: dict = {}


def _get_executor(md_data_file: str = DEFAULT_MD_FILE) -> FormulaExecutor:
    """Get or create a cached FormulaExecutor (shares market-data cache)."""
    if md_data_file not in _executor_cache:
        _executor_cache[md_data_file] = FormulaExecutor(md_data_file=md_data_file)
    return _executor_cache[md_data_file]


def compute_factor_panel(formula: str, md_data_file: str = DEFAULT_MD_FILE) -> pd.DataFrame:
    """Compute a factor's panel DataFrame (date x Ticker) for correlation check."""
    executor = _get_executor(md_data_file)
    return executor.compute(formula)


def spearman_correlation(panel_a: pd.DataFrame, panel_b: pd.DataFrame) -> float:
    """Compute Spearman rank correlation between two factor panels.

    Both panels are flattened and NaN-paired values are used.
    Returns |correlation| (absolute value) since we care about magnitude.

    Implementation: Spearman correlation = Pearson correlation on ranks.
    """
    a = panel_a.values.flatten()
    b = panel_b.values.flatten()
    mask = np.isfinite(a) & np.isfinite(b)
    if mask.sum() < 10:
        return 0.0

    a_clean = a[mask]
    b_clean = b[mask]

    # Rank transform (average method for ties, like scipy default)
    rank_a = pd.Series(a_clean).rank(method='average').values
    rank_b = pd.Series(b_clean).rank(method='average').values

    # Pearson correlation on ranks
    rank_a_mean = rank_a.mean()
    rank_b_mean = rank_b.mean()
    rank_a_centered = rank_a - rank_a_mean
    rank_b_centered = rank_b - rank_b_mean

    cov = np.dot(rank_a_centered, rank_b_centered)
    std_a = np.sqrt(np.dot(rank_a_centered, rank_a_centered))
    std_b = np.sqrt(np.dot(rank_b_centered, rank_b_centered))

    if std_a == 0 or std_b == 0:
        return 0.0

    corr = cov / (std_a * std_b)
    return abs(corr) if np.isfinite(corr) else 0.0


def check_correlation_admission(
    candidates: typing.List[typing.Dict[str, typing.Any]],
    library: memory.mining_state.FactorLibrary,
    corr_threshold: float = 0.5,
    md_data_file: str = DEFAULT_MD_FILE,
    admit: bool = True,
) -> typing.List[typing.Dict[str, typing.Any]]:
    """Check correlation of score-passing candidates against the factor library.

    Args:
        candidates: list of {"formula", "factor_id", "tot_score", "verdict"}
        library: the FactorLibrary instance
        corr_threshold: Spearman |corr| threshold (default 0.5)
        md_data_file: market data file path
        admit: if True, automatically add/replace factors in library.
               if False, only compute correlations and decisions (report-only mode).

    Returns:
        Updated results list with "decision" field added:
        - "admit": low correlation (if admit=True, added to library)
        - "replace": high correlation but higher score (if admit=True, replaces old factor)
        - "reject": high correlation and lower score
        - "skip_score_fail": score didn't pass threshold (not correlation-checked)
        - "panel_error": failed to compute factor panel

    Logic per candidate:
        1. Compute candidate panel via FormulaExecutor
        2. For each library factor, compute its panel and Spearman |corr|
        3. If max |corr| >= threshold:
           - If candidate.tot_score > matched_factor.tot_score → replace
           - Else → reject
        4. If max |corr| < threshold → admit
    """
    existing_records = library.get_records()
    results = []

    # Pre-compute existing factor panels (cache for reuse)
    existing_panels: typing.Dict[str, pd.DataFrame] = {}
    for rec in existing_records:
        try:
            existing_panels[rec.factor_id] = compute_factor_panel(rec.formula, md_data_file)
        except Exception as exc:
            logger.warning("Failed to compute panel for library factor '%s': %s", rec.factor_id, exc)

    for cand in candidates:
        formula = cand["formula"]
        factor_id = cand["factor_id"]
        tot_score = cand["tot_score"]
        verdict = cand.get("verdict", "FAIL")

        # Only correlation-check factors that passed the score threshold
        if verdict != "PASS":
            cand["decision"] = "skip_score_fail"
            results.append(cand)
            continue

        # Compute candidate panel
        try:
            cand_panel = compute_factor_panel(formula, md_data_file)
        except Exception as exc:
            logger.warning("Failed to compute panel for candidate '%s': %s", formula, exc)
            cand["decision"] = "panel_error"
            cand["error"] = str(exc)
            results.append(cand)
            continue

        # Compute Spearman correlation with all existing factors
        max_corr = 0.0
        matched_factor_id = None
        matched_factor_score = 0.0
        matched_factor_formula = ""
        correlations = {}

        for rec in existing_records:
            if rec.factor_id in existing_panels:
                corr = spearman_correlation(cand_panel, existing_panels[rec.factor_id])
                correlations[rec.factor_id] = round(corr, 4)
                if corr > max_corr:
                    max_corr = corr
                    matched_factor_id = rec.factor_id
                    matched_factor_score = rec.tot_score
                    matched_factor_formula = rec.formula

        cand["max_corr"] = round(max_corr, 4)
        cand["matched_factor"] = matched_factor_id
        cand["correlations"] = correlations

        if max_corr >= corr_threshold:
            # High correlation with g★ — check all 3 conditions for replacement:
            # 1. |ρ(α, g★)| ≥ θ (already satisfied)
            # 2. max_{g∈L\{g★}} |ρ(α,g)| < 0.5 (low correlation with OTHER library factors)
            # 3. score(α) > score(g★)

            # Check condition 2: low correlation with all OTHER library factors
            other_corrs = {fid: c for fid, c in correlations.items() if fid != matched_factor_id}
            max_other_corr = max(other_corrs.values()) if other_corrs else 0.0

            if max_other_corr < corr_threshold and tot_score > matched_factor_score:
                # All 3 conditions met — replace old
                cand["decision"] = "replace"
                cand["replaced_factor"] = matched_factor_id
                cand["replaced_score"] = matched_factor_score
                cand["replaced_formula"] = matched_factor_formula
                if admit:
                    # Update library: remove old, add new
                    library.remove_by_id(matched_factor_id)
                    library.add(memory.mining_state.FactorRecord(
                        formula=formula,
                        tot_score=tot_score,
                        factor_name=formula,
                    ))
                    # Remove replaced factor from panels cache
                    existing_panels.pop(matched_factor_id, None)
                    # Get the new factor's auto-assigned ID
                    new_factor_id = library.factors[-1].factor_id
                    existing_panels[new_factor_id] = cand_panel
                    cand["library_factor_id"] = new_factor_id
                    # Update existing_records
                    existing_records = library.get_records()
            else:
                # Condition 2 or 3 failed — reject new
                cand["decision"] = "reject"
                if max_other_corr >= corr_threshold:
                    cand["reason"] = f"corr={max_corr:.4f} with {matched_factor_id} but also corr={max_other_corr:.4f} with other library factors"
                else:
                    cand["reason"] = f"corr={max_corr:.4f} with {matched_factor_id} (score {matched_factor_score:.1f} >= {tot_score:.1f})"
        else:
            # Low correlation — admit directly
            cand["decision"] = "admit"
            if admit:
                library.add(memory.mining_state.FactorRecord(
                    formula=formula,
                    tot_score=tot_score,
                    factor_name=formula,
                ))
                # Get the new factor's auto-assigned ID
                new_factor_id = library.factors[-1].factor_id
                cand["library_factor_id"] = new_factor_id
                # Update panels cache and existing_records
                existing_panels[new_factor_id] = cand_panel
                existing_records = library.get_records()

        results.append(cand)

    return results


def intra_batch_dedup(
    results: typing.List[typing.Dict[str, typing.Any]],
    library: memory.mining_state.FactorLibrary,
    corr_threshold: float = 0.5,
    md_data_file: str = DEFAULT_MD_FILE,
    admit: bool = True,
) -> typing.List[typing.Dict[str, typing.Any]]:
    """Deduplicate within-batch candidates that passed library corr check.

    Runs AFTER check_correlation_admission.  Greedy approach: sort admitted/
    replaced candidates by score descending, iterate and keep each candidate
    only if it has |corr| < threshold with ALL already-kept candidates.
    Lower-scored duplicates are rolled back from the library and marked
    ``decision = "duplicate_intra_batch"``.

    Example — A(55), B(42), C(38) with corr(A,C)=0.62, corr(C,B)=0.58, corr(A,B)=0.31:
      A → kept (survivors=[A])
      B → corr(B,A)=0.31 < 0.5 → kept (survivors=[A,B])
      C → corr(C,A)=0.62 >= 0.5 → duplicate of A — removed
    Result: A and B survive, C removed.

    Args:
        results: output of check_correlation_admission (mutated in-place)
        library: the FactorLibrary instance (duplicates are removed)
        corr_threshold: Spearman |corr| threshold (default 0.5)
        md_data_file: market data file path
        admit: if True, roll back duplicates from library.
               if False, only mark duplicates (no library mutations).

    Returns:
        The same list with duplicates marked and rolled back.
    """
    # Only consider candidates admitted/replaced into the library
    survivor_indices = [
        i for i, c in enumerate(results)
        if c.get("decision") in ("admit", "replace")
    ]
    if len(survivor_indices) <= 1:
        return results

    # Sort by score descending — greedy keeps the best first
    survivor_indices.sort(
        key=lambda i: results[i]["tot_score"], reverse=True
    )

    # Compute panels once
    panels: typing.Dict[int, pd.DataFrame] = {}
    for i in survivor_indices:
        try:
            panels[i] = compute_factor_panel(
                results[i]["formula"], md_data_file
            )
        except Exception as exc:
            logger.warning(
                "Intra-batch dedup: failed panel for '%s': %s",
                results[i]["formula"][:60], exc,
            )

    kept: typing.List[int] = []

    for i in survivor_indices:
        if i not in panels:
            kept.append(i)
            continue

        # Check correlation with all already-kept candidates
        dup_of = None
        dup_corr = 0.0
        for k in kept:
            if k not in panels:
                continue
            corr = spearman_correlation(panels[i], panels[k])
            if corr >= corr_threshold:
                dup_of = k
                dup_corr = corr
                break

        if dup_of is not None:
            if admit:
                # Roll back library admission
                lib_id = results[i].get("library_factor_id")
                if lib_id is not None:
                    library.remove_by_id(lib_id)

                # If this candidate had replaced an existing factor, restore it
                replaced_id = results[i].get("replaced_factor")
                if replaced_id is not None and results[i].get("replaced_score") is not None:
                    replaced_formula = results[i].get("replaced_formula", "")
                    replaced_score = results[i]["replaced_score"]
                    if replaced_formula:
                        library.add(memory.mining_state.FactorRecord(
                            formula=replaced_formula,
                            tot_score=replaced_score,
                            factor_name=replaced_formula,
                        ))

            results[i]["decision"] = "duplicate_intra_batch"
            results[i]["dup_of"] = results[dup_of]["formula"]
            results[i]["dup_corr"] = round(dup_corr, 4)
            results[i].pop("library_factor_id", None)
            logger.info(
                "Intra-batch dup: '%s' (score=%.1f) corr=%.4f with '%s' (score=%.1f) — removed",
                results[i]["formula"][:60], results[i]["tot_score"],
                dup_corr,
                results[dup_of]["formula"][:60], results[dup_of]["tot_score"],
            )
        else:
            kept.append(i)

    return results


# ---------------------------------------------------------------------------
# Evaluator class
# ---------------------------------------------------------------------------
class Evaluator:
    """Evaluation pipeline using tot_score via run_factor + FactorTest."""

    def __init__(
        self,
        eval_fn: typing.Callable[[str], float] = None,
        threshold: float = TOT_SCORE_THRESHOLD,
        md_data_file: str = DEFAULT_MD_FILE,
    ):
        if eval_fn is None:
            eval_fn = lambda formula: tot_score_evaluation(
                formula,
                start_date=20160101,
                end_date=20181231,
            )
        self.eval_fn = eval_fn
        self.threshold = threshold
        self.md_data_file = md_data_file

    def evaluate_single(self, formula: str) -> float:
        """Evaluate a single factor formula and return its tot_score (0-100)."""
        return self.eval_fn(formula)

    def evaluate_batch(
        self,
        formulas: typing.List[str],
        iteration: int = -1,
    ) -> typing.Tuple[typing.List[memory.mining_state.FactorRecord], typing.List[memory.mining_state.FactorRecord]]:
        """Evaluate a batch of candidate factors.

        Returns (success_records, failure_records) where success = tot_score >= threshold.
        """
        successes: typing.List[memory.mining_state.FactorRecord] = []
        failures: typing.List[memory.mining_state.FactorRecord] = []

        for formula in formulas:
            tot_score = self.evaluate_single(formula)
            record = memory.mining_state.FactorRecord(
                factor_id=0,
                factor_name="",  # Will be assigned when admitted to library
                formula=formula,
                tot_score=tot_score,
            )
            if tot_score >= self.threshold:
                successes.append(record)
            else:
                failures.append(record)

        return successes, failures

    def evaluate_and_admit(
        self,
        formulas: typing.List[str],
        iteration: int = -1,
    ) -> typing.Tuple[
        typing.List[memory.mining_state.FactorRecord],
        typing.List[memory.mining_state.FactorRecord],
        typing.List[memory.mining_state.FactorRecord],
    ]:
        """Evaluate batch with intra-batch deduplication.

        Returns (admitted, rejected, duplicates).
        """
        seen: set = set()
        unique_formulas: typing.List[str] = []
        duplicates: typing.List[memory.mining_state.FactorRecord] = []

        for formula in formulas:
            if formula in seen:
                duplicates.append(
                    memory.mining_state.FactorRecord(
                        factor_id=0,
                        factor_name="",  # Will be assigned when admitted to library
                        formula=formula,
                        tot_score=-1.0,
                    )
                )
            else:
                seen.add(formula)
                unique_formulas.append(formula)

        successes, failures = self.evaluate_batch(unique_formulas, iteration)
        return successes, failures, duplicates
