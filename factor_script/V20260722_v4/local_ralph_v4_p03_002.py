"""Sealed candidate from local_ralph_20260722_v4, Pack 03."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 3
CANDIDATE_ID = 'local_ralph_v4_p03_002'
FACTOR_NAME = 'Smoothed_Book_History_Percentile_Discount'
FORMULA = 'Neg(Cs_Rank(Ts_EMA(Ts_Rank(Log(Add(pb, 1)), 40, 20), 10, 5)))'
ECONOMIC_HYPOTHESIS = "Persistently low PB within a stock's own recent history should identify durable balance-sheet discounts while smoothing transient multiple moves."
ECONOMIC_FAMILY = 'valuation_history_reversion'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['valuation_history_reversion']
INTERNAL_SUB_BATCH = 1
