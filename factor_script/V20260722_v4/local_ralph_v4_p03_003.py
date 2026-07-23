"""Sealed candidate from local_ralph_20260722_v4, Pack 03."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 3
CANDIDATE_ID = 'local_ralph_v4_p03_003'
FACTOR_NAME = 'Quiet_Turnover_Book_Value'
FORMULA = 'Neg(Cs_Rank(Mul(Ts_Mean(Log(Add(pb, 1)), 20, 10), Add(Ts_MAD(turn, 20, 10), 0.1))))'
ECONOMIC_HYPOTHESIS = 'Low PB accompanied by stable turnover is less likely to be a short-lived attention shock and should provide a slower-moving value signal.'
ECONOMIC_FAMILY = 'valuation_market_interaction'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['valuation_history_reversion', 'price_volume_turnover_divergence']
INTERNAL_SUB_BATCH = 1
