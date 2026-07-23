"""Sealed candidate from local_ralph_20260722_v4, Pack 02."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 2
CANDIDATE_ID = 'local_ralph_v4_p02_012'
FACTOR_NAME = 'Sales_Multiple_Historical_Percentile_Discount'
FORMULA = 'Neg(Cs_Rank(Ts_Rank(Log(Add(ps, 1)), 100, 50)))'
ECONOMIC_HYPOTHESIS = "A low current PS percentile relative to the stock's own history provides a broadly covered, earnings-independent valuation reversion signal."
ECONOMIC_FAMILY = 'valuation_history_reversion'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['valuation_history_reversion']
INTERNAL_SUB_BATCH = 2
