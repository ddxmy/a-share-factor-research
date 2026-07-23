"""Sealed candidate from local_ralph_20260722_v4, Pack 01."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 1
CANDIDATE_ID = 'local_ralph_v4_p01_039'
FACTOR_NAME = 'High_Volume_Close_Location_Confirmation'
FORMULA = 'Cs_Rank(Ts_Mean(If(Greater(Ts_ZScore(Log(volume), 40, 20), 1), Div(Sub(Mul(2, close), Add(high, low)), Add(Sub(high, low), 0.001)), 0), 40, 20))'
ECONOMIC_HYPOTHESIS = 'Closing near the top of the session range specifically on abnormal-volume days provides stronger evidence of demand than unconditioned close location.'
ECONOMIC_FAMILY = 'signed_volume_accumulation'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['signed_volume_accumulation', 'range_location_anchoring']
INTERNAL_SUB_BATCH = 4
