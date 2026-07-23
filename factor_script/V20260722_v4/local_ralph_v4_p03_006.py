"""Sealed candidate from local_ralph_20260722_v4, Pack 03."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 3
CANDIDATE_ID = 'local_ralph_v4_p03_006'
FACTOR_NAME = 'Lagged_Close_Pressure_Reversal'
FORMULA = 'Neg(Cs_Rank(Ts_EMA(Ts_Delay(Div(Sub(Mul(2, close), Add(high, low)), Add(Sub(high, low), 0.001)), 1), 5, 3)))'
ECONOMIC_HYPOTHESIS = 'Persistent prior-session closing pressure near the edge of the range can reflect temporary end-of-day demand that reverses after the close.'
ECONOMIC_FAMILY = 'price_pressure_reversal'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['price_pressure_reversal', 'Close_Position_Location']
INTERNAL_SUB_BATCH = 1
