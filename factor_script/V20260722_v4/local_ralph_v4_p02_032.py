"""Sealed candidate from local_ralph_20260722_v4, Pack 02."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 2
CANDIDATE_ID = 'local_ralph_v4_p02_032'
FACTOR_NAME = 'Moving_High_Sales_TTM_History_Pressure'
FORMULA = 'Neg(Cs_Rank(Mul(Ts_Rank(Log(Add(ps_ttm, 1)), 100, 50), Add(Abs(Ts_Return(ps_ttm, 10)), 1))))'
ECONOMIC_HYPOTHESIS = 'A high PS-TTM historical percentile is especially vulnerable when the multiple is still moving rapidly, signaling active extrapolative rerating rather than a stable premium.'
ECONOMIC_FAMILY = 'valuation_history_reversion'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['valuation_history_reversion']
INTERNAL_SUB_BATCH = 4
