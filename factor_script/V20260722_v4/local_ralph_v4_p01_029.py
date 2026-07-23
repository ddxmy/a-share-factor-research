"""Sealed candidate from local_ralph_20260722_v4, Pack 01."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 1
CANDIDATE_ID = 'local_ralph_v4_p01_029'
FACTOR_NAME = 'Smoothed_Signed_Turnover_Surprise'
FORMULA = 'Cs_Rank(Ts_EMA(Mul(Sign(Returns), Ts_ZScore(turn, 40, 20)), 8, 4))'
ECONOMIC_HYPOTHESIS = 'A smoothed sequence of directionally signed turnover surprises captures persistent accumulation and distribution while suppressing isolated bursts.'
ECONOMIC_FAMILY = 'signed_volume_accumulation'
DATA_DOMAIN = 'turnover_size_liquidity'
TARGET_PATTERNS = ['signed_volume_accumulation']
INTERNAL_SUB_BATCH = 3
