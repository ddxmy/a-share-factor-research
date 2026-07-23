"""Sealed candidate from local_ralph_20260722_v4, Pack 03."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 3
CANDIDATE_ID = 'local_ralph_v4_p03_024'
FACTOR_NAME = 'Book_Backed_Dividend_Yield'
FORMULA = 'Cs_Rank(Div(Ts_Mean(dv_ttm, 20, 10), Add(Ts_Mean(pb, 20, 10), 0.1)))'
ECONOMIC_HYPOTHESIS = 'Dividend income scaled by smoothed PB favors yield supported by a lower book valuation while avoiding the low-coverage PE-and-dividend intersection.'
ECONOMIC_FAMILY = 'dividend_income_stability'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['dividend_income_stability', 'value_level_composite']
INTERNAL_SUB_BATCH = 3
