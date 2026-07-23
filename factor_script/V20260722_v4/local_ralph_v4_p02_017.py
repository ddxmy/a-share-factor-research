"""Sealed candidate from local_ralph_20260722_v4, Pack 02."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 2
CANDIDATE_ID = 'local_ralph_v4_p02_017'
FACTOR_NAME = 'Range_Sensitivity_Downside_Upside_Gap'
FORMULA = 'Neg(Cs_Rank(Sub(Ts_Beta(Div(Sub(high, low), pre_close), If(Less(Returns, 0), Abs(Returns), 0), 40, 20), Ts_Beta(Div(Sub(high, low), pre_close), If(Greater(Returns, 0), Returns, 0), 40, 20))))'
ECONOMIC_HYPOTHESIS = 'A trading range that expands more elastically with losses than gains reveals latent downside fragility beyond unconditional volatility.'
ECONOMIC_FAMILY = 'volatility_asymmetry'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['volatility_asymmetry']
INTERNAL_SUB_BATCH = 2
