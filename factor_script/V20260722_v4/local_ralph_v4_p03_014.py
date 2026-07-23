"""Sealed candidate from local_ralph_20260722_v4, Pack 03."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 3
CANDIDATE_ID = 'local_ralph_v4_p03_014'
FACTOR_NAME = 'Median_Dividend_Stability_Ratio'
FORMULA = 'Cs_Rank(Div(Ts_Median(dv_ttm, 20, 10), Add(Ts_MAD(dv_ttm, 40, 20), 0.001)))'
ECONOMIC_HYPOTHESIS = 'A high recent median dividend yield relative to its own robust dispersion favors durable income over mechanically volatile yield observations.'
ECONOMIC_FAMILY = 'dividend_income_stability'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['dividend_income_stability']
INTERNAL_SUB_BATCH = 2
