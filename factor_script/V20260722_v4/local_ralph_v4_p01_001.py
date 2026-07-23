"""Sealed candidate from local_ralph_20260722_v4, Pack 01."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 1
CANDIDATE_ID = 'local_ralph_v4_p01_001'
FACTOR_NAME = 'Joint_Earnings_Book_Value_Level'
FORMULA = 'Neg(Cs_Rank(Add(Log(Add(Abs(pe_ttm), 1)), Log(Add(pb, 1)))))'
ECONOMIC_HYPOTHESIS = 'Stocks that are simultaneously inexpensive on trailing earnings and book value may embed an excessive distress discount that mean-reverts after controlling for their joint multiple level.'
ECONOMIC_FAMILY = 'value_level_composite'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['value_level_composite']
INTERNAL_SUB_BATCH = 1
