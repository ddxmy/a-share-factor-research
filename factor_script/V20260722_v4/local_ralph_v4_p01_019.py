"""Sealed candidate from local_ralph_20260722_v4, Pack 01."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 1
CANDIDATE_ID = 'local_ralph_v4_p01_019'
FACTOR_NAME = 'Two_Day_Path_Efficiency'
FORMULA = 'Cs_Rank(Div(Ts_Return(close, 40), Add(Ts_Sum(Abs(Ts_Return(close, 2)), 40, 20), 0.001)))'
ECONOMIC_HYPOTHESIS = 'Forty-day drift supported by small cumulative two-day excursions distinguishes directional repricing from choppy paths with the same endpoint return.'
ECONOMIC_FAMILY = 'trend_quality_path_efficiency'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['trend_quality_path_efficiency']
INTERNAL_SUB_BATCH = 2
