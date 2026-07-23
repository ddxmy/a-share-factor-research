"""Sealed candidate from local_ralph_20260722_v4, Pack 01."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 1
CANDIDATE_ID = 'local_ralph_v4_p01_004'
FACTOR_NAME = 'TTM_Current_Multiple_Consistency_Value'
FORMULA = 'Neg(Cs_Rank(Add(Abs(Sub(Log(Add(Abs(pe_ttm), 1)), Log(Add(Abs(pe), 1)))), Log(Add(Abs(pe_ttm), 1)))))'
ECONOMIC_HYPOTHESIS = 'Cheap firms whose current-basis and trailing earnings multiples agree may be less exposed to transient denominator distortions than equally cheap but internally inconsistent firms.'
ECONOMIC_FAMILY = 'value_level_composite'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['value_level_composite']
INTERNAL_SUB_BATCH = 1
