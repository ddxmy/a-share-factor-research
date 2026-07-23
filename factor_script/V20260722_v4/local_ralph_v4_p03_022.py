"""Sealed candidate from local_ralph_20260722_v4, Pack 03."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 3
CANDIDATE_ID = 'local_ralph_v4_p03_022'
FACTOR_NAME = 'Joint_Book_Sales_History_Discount_Confirmation'
FORMULA = 'Neg(Cs_Rank(Max(Ts_Rank(Log(Add(pb, 1)), 40, 20), Ts_Rank(Log(Add(ps, 1)), 40, 20))))'
ECONOMIC_HYPOTHESIS = 'Using the worse of the two historical percentiles requires both PB and PS to confirm a firm-specific valuation discount.'
ECONOMIC_FAMILY = 'valuation_history_reversion'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['valuation_history_reversion', 'value_level_composite']
INTERNAL_SUB_BATCH = 3
