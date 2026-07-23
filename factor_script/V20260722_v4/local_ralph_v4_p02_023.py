"""Sealed candidate from local_ralph_20260722_v4, Pack 02."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 2
CANDIDATE_ID = 'local_ralph_v4_p02_023'
FACTOR_NAME = 'Sales_Discount_Adjusted_For_Downside_Asymmetry'
FORMULA = 'Cs_Rank(Div(Neg(Ts_Rank(Log(Add(ps, 1)), 100, 50)), Add(Div(Ts_Mean(If(Less(Returns, 0), Power(Returns, 2), 0), 40, 20), Add(Ts_Mean(If(Greater(Returns, 0), Power(Returns, 2), 0), 40, 20), 0.001)), 0.1)))'
ECONOMIC_HYPOTHESIS = 'Historical PS cheapness is more likely to represent mispricing when it is not merely compensation for strongly downside-skewed realized risk.'
ECONOMIC_FAMILY = 'valuation_market_interaction'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['valuation_history_reversion', 'volatility_asymmetry']
INTERNAL_SUB_BATCH = 3
