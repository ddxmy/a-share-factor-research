"""Sealed candidate from local_ralph_20260722_v4, Pack 03."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 3
CANDIDATE_ID = 'local_ralph_v4_p03_025'
FACTOR_NAME = 'Extrema_Ordering_Trend_Confirmation'
FORMULA = 'Cs_Rank(Mul(Sign(Ts_Return(close, 30)), Sub(Ts_ArgMin(low, 30, 15), Ts_ArgMax(high, 30, 15))))'
ECONOMIC_HYPOTHESIS = 'A directional return is more credible when the low and high occur in the expected temporal order, distinguishing trend progression from stale extrema.'
ECONOMIC_FAMILY = 'trend_quality_path_efficiency'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['trend_quality_path_efficiency', 'range_location_anchoring']
INTERNAL_SUB_BATCH = 3
