"""Sealed candidate from local_ralph_20260722_v4, Pack 02."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 2
CANDIDATE_ID = 'local_ralph_v4_p02_021'
FACTOR_NAME = 'Current_TTM_Sales_Consistency_Value'
FORMULA = 'Neg(Cs_Rank(Add(Log(Add(ps_ttm, 1)), Abs(Sub(Log(Add(ps, 1)), Log(Add(ps_ttm, 1)))))))'
ECONOMIC_HYPOTHESIS = 'A low trailing sales multiple is more trustworthy when current-basis and trailing-basis PS agree, filtering denominator timing distortions.'
ECONOMIC_FAMILY = 'value_level_composite'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['value_level_composite']
INTERNAL_SUB_BATCH = 3
