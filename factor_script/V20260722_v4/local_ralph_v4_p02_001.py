"""Sealed candidate from local_ralph_20260722_v4, Pack 02."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 2
CANDIDATE_ID = 'local_ralph_v4_p02_001'
FACTOR_NAME = 'Book_Sales_Level_With_Consistency_Penalty'
FORMULA = 'Neg(Cs_Rank(Add(Add(Log(Add(pb, 1)), Log(Add(ps, 1))), Abs(Sub(Log(Add(pb, 1)), Log(Add(ps, 1)))))))'
ECONOMIC_HYPOTHESIS = 'A low joint PB and PS level is more credible when book- and sales-based multiples agree; penalizing disagreement separates broad cheapness from denominator-specific distortions.'
ECONOMIC_FAMILY = 'value_level_composite'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['value_level_composite']
INTERNAL_SUB_BATCH = 1
