"""Sealed candidate from local_ralph_20260722_v4, Pack 02."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 2
CANDIDATE_ID = 'local_ralph_v4_p02_035'
FACTOR_NAME = 'Signed_Amount_Volume_Accumulation_Gap'
FORMULA = 'Cs_Rank(Sub(Div(Ts_Sum(Mul(Sign(Returns), amt), 20, 10), Add(Ts_Sum(amt, 20, 10), 1)), Div(Ts_Sum(Mul(Sign(Returns), volume), 20, 10), Add(Ts_Sum(volume, 20, 10), 1))))'
ECONOMIC_HYPOTHESIS = 'Divergence between return-signed amount and return-signed share volume separates high-value trade accumulation from broad share-count participation.'
ECONOMIC_FAMILY = 'signed_volume_accumulation'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['signed_volume_accumulation', 'price_volume_turnover_divergence']
INTERNAL_SUB_BATCH = 4
