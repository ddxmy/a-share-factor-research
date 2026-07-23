"""Sealed candidate from local_ralph_20260722_v4, Pack 03."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 3
CANDIDATE_ID = 'local_ralph_v4_p03_033'
FACTOR_NAME = 'Multi_Boundary_Slope_Trend_Coherence'
FORMULA = 'Cs_Rank(Mul(Sign(Slope(Log(close), 30)), Min(Abs(Slope(Log(high), 20)), Abs(Slope(Log(low), 20)))))'
ECONOMIC_HYPOTHESIS = 'A close-price trend confirmed by comparable movement in both high and low boundaries is less likely to be caused by isolated endpoint spikes.'
ECONOMIC_FAMILY = 'trend_quality_path_efficiency'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['trend_quality_path_efficiency']
INTERNAL_SUB_BATCH = 4
