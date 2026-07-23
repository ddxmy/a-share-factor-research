"""Sealed candidate from local_ralph_20260722_v4, Pack 03."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 3
CANDIDATE_ID = 'local_ralph_v4_p03_031'
FACTOR_NAME = 'Relative_Book_Sales_History_Spread_Reversion'
FORMULA = 'Neg(Cs_Rank(Ts_EMA(Sub(Ts_ZScore(Log(Add(pb, 1)), 40, 20), Ts_ZScore(Log(Add(ps_ttm, 1)), 40, 20)), 10, 5)))'
ECONOMIC_HYPOTHESIS = 'A smoothed PB history premium relative to trailing PS isolates cross-denominator overextension that can revert without requiring absolute cheapness.'
ECONOMIC_FAMILY = 'valuation_history_reversion'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['valuation_history_reversion']
INTERNAL_SUB_BATCH = 4
