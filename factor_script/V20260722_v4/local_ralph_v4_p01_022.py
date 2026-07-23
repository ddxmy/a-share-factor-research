"""Sealed candidate from local_ralph_20260722_v4, Pack 01."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 1
CANDIDATE_ID = 'local_ralph_v4_p01_022'
FACTOR_NAME = 'Downside_Upside_Tail_Ratio'
FORMULA = 'Neg(Cs_Rank(Div(Abs(Ts_Quantile(Returns, 40, 0.1, 20)), Add(Abs(Ts_Quantile(Returns, 40, 0.9, 20)), 0.001))))'
ECONOMIC_HYPOTHESIS = 'A dominant downside tail relative to the upside tail indicates asymmetric crash exposure that may remain underpriced by symmetric volatility measures.'
ECONOMIC_FAMILY = 'return_tails_skewness'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['return_tails_skewness']
INTERNAL_SUB_BATCH = 3
