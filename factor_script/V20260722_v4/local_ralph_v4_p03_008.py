"""Sealed candidate from local_ralph_20260722_v4, Pack 03."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 3
CANDIDATE_ID = 'local_ralph_v4_p03_008'
FACTOR_NAME = 'Mean_Downside_Upside_Magnitude_Gap'
FORMULA = 'Neg(Cs_Rank(Div(Ts_Mean(If(Less(Returns, 0), Abs(Returns), 0), 30, 15), Add(Ts_Mean(If(Greater(Returns, 0), Returns, 0), 30, 15), 0.001))))'
ECONOMIC_HYPOTHESIS = 'Average loss magnitude relative to average gain magnitude measures a high-coverage directional volatility asymmetry without sparse tail intersections.'
ECONOMIC_FAMILY = 'volatility_asymmetry'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['volatility_asymmetry']
INTERNAL_SUB_BATCH = 1
