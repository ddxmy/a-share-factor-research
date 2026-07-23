"""Sealed candidate from local_ralph_20260722_v4, Pack 01."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 1
CANDIDATE_ID = 'local_ralph_v4_p01_005'
FACTOR_NAME = 'Earnings_Multiple_History_Discount'
FORMULA = 'Neg(Cs_Rank(Ts_ZScore(Log(Add(Abs(pe_ttm), 1)), 60, 30)))'
ECONOMIC_HYPOTHESIS = 'A trailing earnings multiple below its own medium-horizon norm can indicate a firm-specific valuation discount not captured by a static cross-sectional value rank.'
ECONOMIC_FAMILY = 'valuation_history_reversion'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['valuation_history_reversion']
INTERNAL_SUB_BATCH = 1
