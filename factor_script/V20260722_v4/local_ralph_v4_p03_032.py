"""Sealed candidate from local_ralph_20260722_v4, Pack 03."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 3
CANDIDATE_ID = 'local_ralph_v4_p03_032'
FACTOR_NAME = 'Smoothed_Sales_Rerating_Price_Decoupling'
FORMULA = 'Neg(Cs_Rank(Ts_Correlation(Ts_Delta(Ts_EMA(Log(Add(ps, 1)), 10, 5), 5), Ts_EMA(Returns, 5, 3), 30, 15)))'
ECONOMIC_HYPOTHESIS = 'Persistent decoupling between smoothed sales-multiple changes and smoothed returns indicates rerating unsupported by ordinary price transmission.'
ECONOMIC_FAMILY = 'valuation_market_interaction'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['valuation_history_reversion', 'price_pressure_reversal']
INTERNAL_SUB_BATCH = 4
