"""Sealed candidate from local_ralph_20260722_v4, Pack 03."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 3
CANDIDATE_ID = 'local_ralph_v4_p03_030'
FACTOR_NAME = 'Signed_VWAP_Turnover_Accumulation'
FORMULA = 'Cs_Rank(Ts_Mean(Mul(Sign(Ts_Delta(vwap, 1)), Div(turn, Add(Ts_Mean(turn, 20, 10), 0.1))), 20, 10))'
ECONOMIC_HYPOTHESIS = 'Turnover signed by changes in the traded-price anchor captures persistent accumulation or distribution that is less endpoint-driven than close-signed volume.'
ECONOMIC_FAMILY = 'signed_volume_accumulation'
DATA_DOMAIN = 'turnover_size_liquidity'
TARGET_PATTERNS = ['signed_volume_accumulation', 'VWAP_Deviation_Rank']
INTERNAL_SUB_BATCH = 3
