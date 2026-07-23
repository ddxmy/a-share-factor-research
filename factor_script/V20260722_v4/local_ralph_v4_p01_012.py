"""Sealed candidate from local_ralph_20260722_v4, Pack 01."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 1
CANDIDATE_ID = 'local_ralph_v4_p01_012'
FACTOR_NAME = 'Sales_Compression_With_Price_Confirmation'
FORMULA = 'Cs_Rank(Mul(Neg(Ts_ZScore(Log(Add(ps_ttm, 1)), 60, 30)), Ts_Return(close, 20)))'
ECONOMIC_HYPOTHESIS = 'A historically compressed sales multiple combined with improving price action can mark the early confirmation of a fundamental rerating rather than an unresolved value trap.'
ECONOMIC_FAMILY = 'valuation_market_interaction'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['trend_quality_path_efficiency']
INTERNAL_SUB_BATCH = 2
