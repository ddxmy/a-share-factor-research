"""Sealed candidate from local_ralph_20260722_v4, Pack 02."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 2
CANDIDATE_ID = 'local_ralph_v4_p02_025'
FACTOR_NAME = 'Multiscale_Slope_Direction_Coherence'
FORMULA = 'Cs_Rank(Mul(Sign(Slope(Log(close), 60)), Ts_Correlation(Ts_Delta(Ts_WMA(Log(close), 10, 5), 1), Ts_Delta(Ts_WMA(Log(close), 30, 15), 1), 40, 20)))'
ECONOMIC_HYPOTHESIS = 'A long-horizon trend is higher quality when short- and medium-scale smoothed price slopes move together rather than oscillating across scales.'
ECONOMIC_FAMILY = 'trend_quality_path_efficiency'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['trend_quality_path_efficiency']
INTERNAL_SUB_BATCH = 3
