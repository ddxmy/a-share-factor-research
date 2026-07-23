"""Sealed candidate from local_ralph_20260722_v4, Pack 02."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 2
CANDIDATE_ID = 'local_ralph_v4_p02_004'
FACTOR_NAME = 'Volume_Attended_Sales_History_Discount'
FORMULA = 'Cs_Rank(Mul(Neg(Ts_Rank(Log(Add(ps, 1)), 80, 40)), Ts_ZScore(Log(volume), 20, 10)))'
ECONOMIC_HYPOTHESIS = 'A low historical PS position accompanied by unusual trading volume is more likely to represent active repricing than a stale, unattended valuation quote.'
ECONOMIC_FAMILY = 'valuation_market_interaction'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['valuation_history_reversion', 'price_volume_turnover_divergence']
INTERNAL_SUB_BATCH = 1
