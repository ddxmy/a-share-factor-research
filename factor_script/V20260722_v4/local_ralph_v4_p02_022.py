"""Sealed candidate from local_ralph_20260722_v4, Pack 02."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 2
CANDIDATE_ID = 'local_ralph_v4_p02_022'
FACTOR_NAME = 'Sales_TTM_Historical_ZScore_Acceleration_Reversal'
FORMULA = 'Neg(Cs_Rank(Ts_Delta(Ts_ZScore(Log(Add(ps_ttm, 1)), 80, 40), 5)))'
ECONOMIC_HYPOTHESIS = "A rapid rise in a stock's historical PS-TTM z-score reflects abrupt multiple expansion that is more likely to mean-revert than a stable level."
ECONOMIC_FAMILY = 'valuation_history_reversion'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['valuation_history_reversion']
INTERNAL_SUB_BATCH = 3
