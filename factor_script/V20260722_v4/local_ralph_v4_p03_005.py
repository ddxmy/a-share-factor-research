"""Sealed candidate from local_ralph_20260722_v4, Pack 03."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 3
CANDIDATE_ID = 'local_ralph_v4_p03_005'
FACTOR_NAME = 'Slope_To_Return_Noise_Trend'
FORMULA = 'Cs_Rank(Div(Slope(Log(close), 30), Add(Ts_MAD(Returns, 30, 15), 0.001)))'
ECONOMIC_HYPOTHESIS = 'Log-price slope scaled by robust return noise favors orderly drift over paths whose endpoint trend is dominated by dispersion.'
ECONOMIC_FAMILY = 'trend_quality_path_efficiency'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['trend_quality_path_efficiency']
INTERNAL_SUB_BATCH = 1
