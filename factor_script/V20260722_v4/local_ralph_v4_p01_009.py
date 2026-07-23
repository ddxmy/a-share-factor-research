"""Sealed candidate from local_ralph_20260722_v4, Pack 01."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 1
CANDIDATE_ID = 'local_ralph_v4_p01_009'
FACTOR_NAME = 'Book_Value_Price_Dislocation'
FORMULA = 'Neg(Cs_Rank(Mul(Log(Add(pb, 1)), Add(Abs(Ts_Return(close, 20)), 1))))'
ECONOMIC_HYPOTHESIS = 'A book-value discount is more informative after a material price displacement, when forced repricing can push already-cheap securities further from fundamental anchors.'
ECONOMIC_FAMILY = 'valuation_market_interaction'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['trend_quality_path_efficiency']
INTERNAL_SUB_BATCH = 1
