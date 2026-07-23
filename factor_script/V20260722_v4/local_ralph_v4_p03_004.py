"""Sealed candidate from local_ralph_20260722_v4, Pack 03."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 3
CANDIDATE_ID = 'local_ralph_v4_p03_004'
FACTOR_NAME = 'Smoothed_Dividend_Yield_Level'
FORMULA = 'Cs_Rank(Ts_EMA(dv_ttm, 20, 10))'
ECONOMIC_HYPOTHESIS = 'A dividend yield that remains elevated after short smoothing is more likely to represent persistent income compensation than a one-day endpoint change.'
ECONOMIC_FAMILY = 'dividend_income_stability'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['dividend_income_stability']
INTERNAL_SUB_BATCH = 1
