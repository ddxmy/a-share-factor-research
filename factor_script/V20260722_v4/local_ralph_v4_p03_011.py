"""Sealed candidate from local_ralph_20260722_v4, Pack 03."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 3
CANDIDATE_ID = 'local_ralph_v4_p03_011'
FACTOR_NAME = 'Conservative_Max_Book_Sales_Value'
FORMULA = 'Neg(Cs_Rank(Max(Log(Add(pb, 1)), Log(Add(ps, 1)))))'
ECONOMIC_HYPOTHESIS = 'Ranking the more expensive of PB and PS rewards stocks that are cheap on both dimensions and prevents one extreme denominator from dominating the composite.'
ECONOMIC_FAMILY = 'value_level_composite'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['value_level_composite']
INTERNAL_SUB_BATCH = 2
