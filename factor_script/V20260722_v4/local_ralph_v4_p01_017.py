"""Sealed candidate from local_ralph_20260722_v4, Pack 01."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 1
CANDIDATE_ID = 'local_ralph_v4_p01_017'
FACTOR_NAME = 'Persistent_Dividend_Yield_Quality'
FORMULA = 'Cs_Rank(Div(Ts_Mean(dv_ttm, 60, 30), Add(Ts_MAD(dv_ttm, 60, 30), 0.001)))'
ECONOMIC_HYPOTHESIS = 'A high dividend yield sustained with low historical dispersion is more likely to reflect durable shareholder income than a one-day mechanical spike.'
ECONOMIC_FAMILY = 'dividend_income_stability'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['dividend_income_stability']
INTERNAL_SUB_BATCH = 2
