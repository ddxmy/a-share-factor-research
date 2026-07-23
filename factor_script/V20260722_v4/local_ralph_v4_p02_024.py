"""Sealed candidate from local_ralph_20260722_v4, Pack 02."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 2
CANDIDATE_ID = 'local_ralph_v4_p02_024'
FACTOR_NAME = 'Book_Rerating_Amount_Coupling_Reversal'
FORMULA = 'Neg(Cs_Rank(Ts_Correlation(Ts_Delta(Log(Add(pb, 1)), 1), Ts_Delta(Log(amt), 1), 80, 40)))'
ECONOMIC_HYPOTHESIS = 'Strong persistent co-movement between daily PB changes and trading-amount changes identifies attention-driven rerating that is vulnerable to reversal.'
ECONOMIC_FAMILY = 'valuation_market_interaction'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['valuation_history_reversion', 'price_volume_turnover_divergence']
INTERNAL_SUB_BATCH = 3
