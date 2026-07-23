"""Sealed candidate from local_ralph_20260722_v4, Pack 03."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 3
CANDIDATE_ID = 'local_ralph_v4_p03_001'
FACTOR_NAME = 'Smoothed_Book_Sales_Value'
FORMULA = 'Neg(Cs_Rank(Ts_EMA(Add(Log(Add(pb, 1)), Log(Add(ps_ttm, 1))), 20, 10)))'
ECONOMIC_HYPOTHESIS = 'A smoothed joint PB and trailing-PS level captures broad cheapness while reducing daily rank churn and avoiding dependence on earnings or dividend coverage.'
ECONOMIC_FAMILY = 'value_level_composite'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['value_level_composite']
INTERNAL_SUB_BATCH = 1
