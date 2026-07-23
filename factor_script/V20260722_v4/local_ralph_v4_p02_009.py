"""Sealed candidate from local_ralph_20260722_v4, Pack 02."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 2
CANDIDATE_ID = 'local_ralph_v4_p02_009'
FACTOR_NAME = 'Price_Trend_Orthogonal_To_Turnover_Trend'
FORMULA = 'Neg(Cs_Rank(Ts_Residual(Ts_Return(close, 20), Ts_Return(turn, 20), 60, 30)))'
ECONOMIC_HYPOTHESIS = 'Price trends not explained by contemporaneous turnover trends are more likely to be unsupported pressure and subsequently reverse.'
ECONOMIC_FAMILY = 'price_volume_turnover_divergence'
DATA_DOMAIN = 'turnover_size_liquidity'
TARGET_PATTERNS = ['price_volume_turnover_divergence']
INTERNAL_SUB_BATCH = 1
