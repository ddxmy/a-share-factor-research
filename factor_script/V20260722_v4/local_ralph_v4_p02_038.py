"""Sealed candidate from local_ralph_20260722_v4, Pack 02."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 2
CANDIDATE_ID = 'local_ralph_v4_p02_038'
FACTOR_NAME = 'Lagged_Close_VWAP_Pressure_With_Amount'
FORMULA = 'Neg(Cs_Rank(Mul(Ts_Delay(Div(Sub(close, vwap), vwap), 1), Div(amt, Add(Ts_Mean(amt, 20, 10), 1)))))'
ECONOMIC_HYPOTHESIS = 'A prior close displaced from VWAP on high current amount represents residual inventory pressure that tends to reverse rather than a mere price-only deviation.'
ECONOMIC_FAMILY = 'price_pressure_reversal'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['price_pressure_reversal', 'VWAP_ZScore_Reversion']
INTERNAL_SUB_BATCH = 4
