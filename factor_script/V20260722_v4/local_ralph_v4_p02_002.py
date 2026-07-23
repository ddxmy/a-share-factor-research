"""Sealed candidate from local_ralph_20260722_v4, Pack 02."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 2
CANDIDATE_ID = 'local_ralph_v4_p02_002'
FACTOR_NAME = 'Book_Multiple_Historical_Percentile_Discount'
FORMULA = 'Neg(Cs_Rank(Ts_Rank(Log(Add(pb, 1)), 120, 60)))'
ECONOMIC_HYPOTHESIS = 'A stock near the low end of its own long PB history may carry an excessive balance-sheet discount that mean-reverts without requiring earnings or dividend coverage.'
ECONOMIC_FAMILY = 'valuation_history_reversion'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['valuation_history_reversion']
INTERNAL_SUB_BATCH = 1
