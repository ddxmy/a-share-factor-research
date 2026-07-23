"""Sealed candidate from local_ralph_20260722_v4, Pack 02."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 2
CANDIDATE_ID = 'local_ralph_v4_p02_033'
FACTOR_NAME = 'Sales_Rerating_Orthogonal_To_Price'
FORMULA = 'Neg(Cs_Rank(Ts_Residual(Ts_Delta(Log(Add(ps, 1)), 5), Ts_Return(close, 5), 60, 30)))'
ECONOMIC_HYPOTHESIS = 'The component of PS rerating unexplained by concurrent price returns may reflect denominator timing or transient repricing and should revert.'
ECONOMIC_FAMILY = 'valuation_market_interaction'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['valuation_history_reversion', 'price_pressure_reversal']
INTERNAL_SUB_BATCH = 4
