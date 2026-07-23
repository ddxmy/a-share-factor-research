"""Sealed candidate from local_ralph_20260722_v4, Pack 02."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 2
CANDIDATE_ID = 'local_ralph_v4_p02_020'
FACTOR_NAME = 'Gap_Direction_Opening_Location_Imprint'
FORMULA = 'Cs_Rank(Ts_Mean(Mul(Sign(Div(Sub(open, pre_close), pre_close)), Div(Sub(open, low), Add(Sub(high, low), 0.001))), 40, 20))'
ECONOMIC_HYPOTHESIS = "The location of the open inside the day's range conditions whether overnight gap direction leaves a durable session imprint or is immediately rejected."
ECONOMIC_FAMILY = 'overnight_intraday_decomposition'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['overnight_intraday_decomposition', 'range_location_anchoring']
INTERNAL_SUB_BATCH = 2
