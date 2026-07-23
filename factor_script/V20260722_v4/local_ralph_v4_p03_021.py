"""Sealed candidate from local_ralph_20260722_v4, Pack 03."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 3
CANDIDATE_ID = 'local_ralph_v4_p03_021'
FACTOR_NAME = 'Stable_Joint_Book_Sales_Rank_Value'
FORMULA = 'Neg(Add(Cs_Rank(Ts_Median(Log(Add(pb, 1)), 20, 10)), Cs_Rank(Ts_Median(Log(Add(ps_ttm, 1)), 20, 10))))'
ECONOMIC_HYPOTHESIS = 'Adding cross-sectional ranks of smoothed PB and trailing PS creates a stable broad-value composite without relying on the scale of either multiple.'
ECONOMIC_FAMILY = 'value_level_composite'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['value_level_composite']
INTERNAL_SUB_BATCH = 3
