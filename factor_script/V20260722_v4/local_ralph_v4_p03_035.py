"""Sealed candidate from local_ralph_20260722_v4, Pack 03."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 3
CANDIDATE_ID = 'local_ralph_v4_p03_035'
FACTOR_NAME = 'Stable_Median_Amihud_Pressure'
FORMULA = 'Neg(Cs_Rank(Ts_Median(Div(Abs(Returns), Add(amt, 1)), 20, 10)))'
ECONOMIC_HYPOTHESIS = 'The rolling median of absolute return per unit amount measures persistent price impact while suppressing isolated liquidity shocks.'
ECONOMIC_FAMILY = 'liquidity_amount_shocks'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['liquidity_amount_shocks']
INTERNAL_SUB_BATCH = 4
