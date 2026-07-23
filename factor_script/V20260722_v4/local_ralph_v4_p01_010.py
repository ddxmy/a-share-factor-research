"""Sealed candidate from local_ralph_20260722_v4, Pack 01."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 1
CANDIDATE_ID = 'local_ralph_v4_p01_010'
FACTOR_NAME = 'Turnover_Weighted_Earnings_Expensiveness'
FORMULA = 'Neg(Cs_Rank(Mul(Log(Add(Abs(pe_ttm), 1)), Add(Ts_Mean(turn, 20, 10), 0.1))))'
ECONOMIC_HYPOTHESIS = 'Expensive earnings multiples accompanied by persistently high turnover may reflect crowded attention, while low multiples without such crowding retain greater rerating capacity.'
ECONOMIC_FAMILY = 'valuation_market_interaction'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['price_volume_turnover_divergence']
INTERNAL_SUB_BATCH = 1
