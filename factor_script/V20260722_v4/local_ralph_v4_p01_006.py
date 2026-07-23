"""Sealed candidate from local_ralph_20260722_v4, Pack 01."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 1
CANDIDATE_ID = 'local_ralph_v4_p01_006'
FACTOR_NAME = 'Book_Multiple_History_Discount'
FORMULA = 'Neg(Cs_Rank(Ts_ZScore(Log(Add(pb, 1)), 80, 40)))'
ECONOMIC_HYPOTHESIS = 'A price-to-book ratio unusually low relative to its own history may capture temporary balance-sheet pessimism and subsequent normalization.'
ECONOMIC_FAMILY = 'valuation_history_reversion'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['valuation_history_reversion']
INTERNAL_SUB_BATCH = 1
