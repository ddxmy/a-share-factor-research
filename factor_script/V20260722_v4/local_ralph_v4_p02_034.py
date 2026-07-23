"""Sealed candidate from local_ralph_20260722_v4, Pack 02."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 2
CANDIDATE_ID = 'local_ralph_v4_p02_034'
FACTOR_NAME = 'Skew_Adjusted_Sales_TTM_History_Discount'
FORMULA = 'Cs_Rank(Div(Neg(Ts_Rank(Log(Add(ps_ttm, 1)), 100, 50)), Add(Abs(Ts_Skewness(Returns, 60, 30)), 1)))'
ECONOMIC_HYPOTHESIS = 'Historical PS-TTM cheapness is more credible when it is not paired with extreme return skewness that could proxy for unresolved event risk.'
ECONOMIC_FAMILY = 'valuation_market_interaction'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['valuation_history_reversion', 'return_tails_skewness']
INTERNAL_SUB_BATCH = 4
