"""Sealed candidate from local_ralph_20260722_v4, Pack 02."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 2
CANDIDATE_ID = 'local_ralph_v4_p02_016'
FACTOR_NAME = 'Volume_Confirmed_Upper_Tail_Excess'
FORMULA = 'Neg(Cs_Rank(Ts_Mean(If(Greater(Returns, Ts_Quantile(Returns, 60, 0.9, 30)), Mul(Returns, Div(volume, Add(Ts_Mean(volume, 20, 10), 1))), 0), 60, 30)))'
ECONOMIC_HYPOTHESIS = 'Repeated upper-tail returns carrying exceptional volume proxy for crowded attention and lottery demand whose price impact tends to unwind.'
ECONOMIC_FAMILY = 'return_tails_skewness'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['return_tails_skewness', 'price_volume_turnover_divergence']
INTERNAL_SUB_BATCH = 2
