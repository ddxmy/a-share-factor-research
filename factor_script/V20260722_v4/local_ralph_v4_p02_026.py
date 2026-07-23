"""Sealed candidate from local_ralph_20260722_v4, Pack 02."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 2
CANDIDATE_ID = 'local_ralph_v4_p02_026'
FACTOR_NAME = 'Absolute_Return_Tail_Clustering'
FORMULA = 'Neg(Cs_Rank(Ts_Correlation(If(Greater(Abs(Returns), Ts_Quantile(Abs(Returns), 60, 0.9, 30)), 1, 0), Ts_Delay(If(Greater(Abs(Returns), Ts_Quantile(Abs(Returns), 60, 0.9, 30)), 1, 0), 1), 60, 30)))'
ECONOMIC_HYPOTHESIS = 'Temporal clustering of extreme absolute returns signals persistent jump risk and attention-driven instability not captured by tail magnitude alone.'
ECONOMIC_FAMILY = 'return_tails_skewness'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['return_tails_skewness', 'volatility_asymmetry']
INTERNAL_SUB_BATCH = 3
