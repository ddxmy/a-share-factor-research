"""Sealed candidate from local_ralph_20260722_v4, Pack 03."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 3
CANDIDATE_ID = 'local_ralph_v4_p03_016'
FACTOR_NAME = 'Upper_Wick_Amount_Exhaustion'
FORMULA = 'Neg(Cs_Rank(Ts_Mean(Mul(Div(Sub(high, Max(open, close)), Add(Sub(high, low), 0.001)), Div(amt, Add(Ts_Mean(amt, 20, 10), 1))), 20, 10)))'
ECONOMIC_HYPOTHESIS = 'Repeated upper wicks carrying high relative trading amount indicate absorbed buying pressure and a slower-moving exhaustion signal.'
ECONOMIC_FAMILY = 'price_pressure_reversal'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['price_pressure_reversal', 'price_volume_turnover_divergence']
INTERNAL_SUB_BATCH = 2
