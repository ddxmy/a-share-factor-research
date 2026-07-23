"""Sealed candidate from local_ralph_20260722_v4, Pack 02."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 2
CANDIDATE_ID = 'local_ralph_v4_p02_007'
FACTOR_NAME = 'Downside_Upside_Semivariance_Acceleration_Gap'
FORMULA = 'Neg(Cs_Rank(Sub(Div(Ts_Mean(If(Less(Returns, 0), Power(Returns, 2), 0), 10, 5), Add(Ts_Mean(If(Less(Returns, 0), Power(Returns, 2), 0), 40, 20), 0.001)), Div(Ts_Mean(If(Greater(Returns, 0), Power(Returns, 2), 0), 10, 5), Add(Ts_Mean(If(Greater(Returns, 0), Power(Returns, 2), 0), 40, 20), 0.001)))))'
ECONOMIC_HYPOTHESIS = 'A sharper short-run acceleration of downside semivariance than upside semivariance signals newly asymmetric risk that prices may not yet fully absorb.'
ECONOMIC_FAMILY = 'volatility_asymmetry'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['volatility_asymmetry']
INTERNAL_SUB_BATCH = 1
