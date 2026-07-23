"""Sealed candidate from local_ralph_20260722_v4, Pack 02."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 2
CANDIDATE_ID = 'local_ralph_v4_p02_011'
FACTOR_NAME = 'Historical_Book_Sales_Rank_Coherence'
FORMULA = 'Neg(Cs_Rank(Add(Ts_Rank(Log(Add(pb, 1)), 80, 40), Abs(Sub(Ts_Rank(Log(Add(pb, 1)), 80, 40), Ts_Rank(Log(Add(ps_ttm, 1)), 80, 40))))))'
ECONOMIC_HYPOTHESIS = 'Low PB is more reliable when PB and trailing PS occupy similar historical percentiles, reducing single-denominator false-value exposure.'
ECONOMIC_FAMILY = 'value_level_composite'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['value_level_composite', 'valuation_history_reversion']
INTERNAL_SUB_BATCH = 2
