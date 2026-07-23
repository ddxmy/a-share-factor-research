"""Sealed candidate from local_ralph_20260722_v4, Pack 02."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 2
CANDIDATE_ID = 'local_ralph_v4_p02_015'
FACTOR_NAME = 'Median_Detrended_Path_Efficiency'
FORMULA = 'Cs_Rank(Div(Ts_Return(close, 50), Add(Ts_Sum(Abs(Sub(Returns, Ts_Median(Returns, 20, 10))), 50, 25), 0.001)))'
ECONOMIC_HYPOTHESIS = 'Directional return earned with little return-path deviation from a rolling local median indicates an orderly trend rather than a few discontinuous jumps.'
ECONOMIC_FAMILY = 'trend_quality_path_efficiency'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['trend_quality_path_efficiency']
INTERNAL_SUB_BATCH = 2
