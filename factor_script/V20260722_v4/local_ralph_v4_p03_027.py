"""Sealed candidate from local_ralph_20260722_v4, Pack 03."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 3
CANDIDATE_ID = 'local_ralph_v4_p03_027'
FACTOR_NAME = 'Post_Lower_Tail_Recovery'
FORMULA = 'Cs_Rank(Ts_Mean(If(Less(Ts_Delay(Returns, 1), Ts_Delay(Ts_Quantile(Returns, 40, 0.1, 20), 1)), Returns, 0), 40, 20))'
ECONOMIC_HYPOTHESIS = 'Average next-session performance after lower-tail losses measures whether stress is routinely absorbed or continues, complementing unconditional tail magnitude.'
ECONOMIC_FAMILY = 'return_tails_skewness'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['return_tails_skewness', 'price_pressure_reversal']
INTERNAL_SUB_BATCH = 3
