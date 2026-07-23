"""Sealed candidate from local_ralph_20260722_v4, Pack 02."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 2
CANDIDATE_ID = 'local_ralph_v4_p02_005'
FACTOR_NAME = 'Channel_Boundary_Coherent_Trend'
FORMULA = 'Cs_Rank(Mul(Sign(Ts_Return(close, 60)), Ts_Correlation(Ts_Delta(high, 1), Ts_Delta(low, 1), 40, 20)))'
ECONOMIC_HYPOTHESIS = 'Trends are higher quality when daily highs and lows migrate together rather than through isolated spikes; boundary co-movement confirms the direction of the long return.'
ECONOMIC_FAMILY = 'trend_quality_path_efficiency'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['trend_quality_path_efficiency']
INTERNAL_SUB_BATCH = 1
