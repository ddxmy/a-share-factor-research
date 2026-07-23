"""Sealed candidate from local_ralph_20260722_v4, Pack 01."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 1
CANDIDATE_ID = 'local_ralph_v4_p01_011'
FACTOR_NAME = 'Volatility_Amplified_Book_Discount'
FORMULA = 'Neg(Cs_Rank(Mul(Ts_ZScore(Log(Add(pb, 1)), 60, 30), Add(Volatility_Ratio(5, 20), 0.1))))'
ECONOMIC_HYPOTHESIS = 'Historically cheap book multiples reached during short-term volatility expansion may reflect liquidity-driven overshooting rather than a permanent impairment.'
ECONOMIC_FAMILY = 'valuation_market_interaction'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['volatility_asymmetry', 'conditional_regimes']
INTERNAL_SUB_BATCH = 2
