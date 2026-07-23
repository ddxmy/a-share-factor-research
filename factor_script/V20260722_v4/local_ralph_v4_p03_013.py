"""Sealed candidate from local_ralph_20260722_v4, Pack 03."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 3
CANDIDATE_ID = 'local_ralph_v4_p03_013'
FACTOR_NAME = 'Quiet_Turnover_Sales_Value'
FORMULA = 'Neg(Cs_Rank(Mul(Ts_Median(Log(Add(ps, 1)), 20, 10), Add(Ts_MAD(turn, 20, 10), 0.1))))'
ECONOMIC_HYPOTHESIS = 'Low PS is more credible when recent turnover is stable, separating slow franchise repricing from value readings created by unstable attention.'
ECONOMIC_FAMILY = 'valuation_market_interaction'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['valuation_history_reversion', 'price_volume_turnover_divergence']
INTERNAL_SUB_BATCH = 2
