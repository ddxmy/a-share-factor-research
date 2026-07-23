"""Sealed candidate from local_ralph_20260722_v4, Pack 02."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 2
CANDIDATE_ID = 'local_ralph_v4_p02_014'
FACTOR_NAME = 'Dividend_History_Persistence_To_Dispersion'
FORMULA = 'Cs_Rank(Mul(Ts_Rank(dv_ttm, 100, 50), Div(Ts_Mean(dv_ttm, 20, 10), Add(Ts_Std(dv_ttm, 60, 30), 0.001))))'
ECONOMIC_HYPOTHESIS = 'High dividend yield is more credible when it remains high in its own history and its recent mean is large relative to long-run variability.'
ECONOMIC_FAMILY = 'dividend_income_stability'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['dividend_income_stability']
INTERNAL_SUB_BATCH = 2
