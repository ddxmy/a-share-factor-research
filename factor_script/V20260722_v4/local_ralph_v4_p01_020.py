"""Sealed candidate from local_ralph_20260722_v4, Pack 01."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 1
CANDIDATE_ID = 'local_ralph_v4_p01_020'
FACTOR_NAME = 'VWAP_Range_Recency_Anchor'
FORMULA = 'Cs_Rank(Sub(Div(Sub(vwap, Ts_Min(low, 40, 20)), Add(Sub(Ts_Max(high, 40, 20), Ts_Min(low, 40, 20)), 0.001)), Div(Ts_ArgMax(high, 40, 20), 40)))'
ECONOMIC_HYPOTHESIS = 'A high VWAP within the medium-term range is more credible when the range high is recent, combining traded-price anchoring with extrema timing.'
ECONOMIC_FAMILY = 'range_location_anchoring'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['range_location_anchoring']
INTERNAL_SUB_BATCH = 2
