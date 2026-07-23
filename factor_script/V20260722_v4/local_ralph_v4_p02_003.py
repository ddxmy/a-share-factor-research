"""Sealed candidate from local_ralph_20260722_v4, Pack 02."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 2
CANDIDATE_ID = 'local_ralph_v4_p02_003'
FACTOR_NAME = 'Book_Rerating_Price_Coupling_Reversal'
FORMULA = 'Neg(Cs_Rank(Ts_Correlation(Ts_Delta(Log(Add(pb, 1)), 5), Returns, 60, 30)))'
ECONOMIC_HYPOTHESIS = 'Persistent same-direction coupling between PB rerating and returns indicates price-led multiple chasing; unusually strong coupling should be vulnerable to reversal.'
ECONOMIC_FAMILY = 'valuation_market_interaction'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['valuation_history_reversion', 'price_pressure_reversal']
INTERNAL_SUB_BATCH = 1
