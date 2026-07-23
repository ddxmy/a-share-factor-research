"""Sealed candidate from local_ralph_20260722_v4, Pack 03."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 3
CANDIDATE_ID = 'local_ralph_v4_p03_015'
FACTOR_NAME = 'EMA_Detrended_Path_Efficiency'
FORMULA = 'Cs_Rank(Div(Ts_Return(close, 30), Add(Ts_Sum(Abs(Sub(Returns, Ts_EMA(Returns, 5, 3))), 30, 15), 0.001)))'
ECONOMIC_HYPOTHESIS = 'Medium-horizon return earned with little deviation from a fast local return trend signals a coherent path rather than isolated jumps.'
ECONOMIC_FAMILY = 'trend_quality_path_efficiency'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['trend_quality_path_efficiency', 'Smoothed_Momentum']
INTERNAL_SUB_BATCH = 2
