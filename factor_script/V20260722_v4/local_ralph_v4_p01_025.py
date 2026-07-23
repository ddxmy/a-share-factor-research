"""Sealed candidate from local_ralph_20260722_v4, Pack 01."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 1
CANDIDATE_ID = 'local_ralph_v4_p01_025'
FACTOR_NAME = 'Intraday_Direction_Volume_Surprise_Persistence'
FORMULA = 'Cs_Rank(Ts_Correlation(Sign(Sub(close, open)), Ts_ZScore(Log(volume), 40, 20), 40, 20))'
ECONOMIC_HYPOTHESIS = 'Persistent alignment of intraday direction with volume surprises indicates informed accumulation or distribution rather than unsigned activity.'
ECONOMIC_FAMILY = 'signed_volume_accumulation'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['signed_volume_accumulation']
INTERNAL_SUB_BATCH = 3
