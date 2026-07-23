"""Sealed candidate from local_ralph_20260722_v4, Pack 03."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 3
CANDIDATE_ID = 'local_ralph_v4_p03_023'
FACTOR_NAME = 'Book_Discount_Smoothed_Price_Recovery'
FORMULA = 'Cs_Rank(Mul(Sub(1, Ts_EMA(Ts_Rank(Log(Add(pb, 1)), 40, 20), 10, 5)), Ts_EMA(Ts_Return(close, 10), 10, 5)))'
ECONOMIC_HYPOTHESIS = 'A persistent PB discount becomes more actionable when accompanied by a smoothed price recovery rather than a one-day rebound.'
ECONOMIC_FAMILY = 'valuation_market_interaction'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['valuation_history_reversion', 'trend_quality_path_efficiency']
INTERNAL_SUB_BATCH = 3
