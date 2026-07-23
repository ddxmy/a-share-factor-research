"""Sealed candidate from local_ralph_20260722_v4, Pack 01."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 1
CANDIDATE_ID = 'local_ralph_v4_p01_013'
FACTOR_NAME = 'Path_Efficient_Earnings_Discount'
FORMULA = 'Cs_Rank(Div(Neg(Ts_ZScore(Log(Add(Abs(pe_ttm), 1)), 60, 30)), Add(Ts_Sum(Abs(Returns), 20, 10), 0.001)))'
ECONOMIC_HYPOTHESIS = 'An earnings-multiple discount accompanied by a relatively orderly price path may represent deliberate repricing with less unresolved noise than an equally cheap but turbulent path.'
ECONOMIC_FAMILY = 'valuation_market_interaction'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['trend_quality_path_efficiency']
INTERNAL_SUB_BATCH = 2
