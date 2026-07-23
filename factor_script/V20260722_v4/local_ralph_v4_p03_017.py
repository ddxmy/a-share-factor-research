"""Sealed candidate from local_ralph_20260722_v4, Pack 03."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 3
CANDIDATE_ID = 'local_ralph_v4_p03_017'
FACTOR_NAME = 'Signed_Third_Moment_Lottery_Aversion'
FORMULA = 'Neg(Cs_Rank(Ts_Mean(SignedPower(Returns, 3), 30, 15)))'
ECONOMIC_HYPOTHESIS = 'The smoothed signed third moment penalizes persistent upside-tail concentration associated with lottery demand while retaining the direction of tail imbalance.'
ECONOMIC_FAMILY = 'return_tails_skewness'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['return_tails_skewness']
INTERNAL_SUB_BATCH = 2
