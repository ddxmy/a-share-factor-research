"""Sealed candidate from local_ralph_20260722_v4, Pack 01."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 1
CANDIDATE_ID = 'local_ralph_v4_p01_016'
FACTOR_NAME = 'Risk_Adjusted_Dividend_Yield'
FORMULA = 'Cs_Rank(Div(dv_ttm, Add(Ts_Std(Returns, 20, 10), 0.001)))'
ECONOMIC_HYPOTHESIS = 'Dividend yield scaled by realized volatility favors income that is less likely to be compensation for unstable price risk.'
ECONOMIC_FAMILY = 'dividend_income_stability'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['volatility_asymmetry']
INTERNAL_SUB_BATCH = 2
