"""Sealed candidate from local_ralph_20260722_v4, Pack 02."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 2
CANDIDATE_ID = 'local_ralph_v4_p02_027'
FACTOR_NAME = 'Conditional_Return_MAD_Asymmetry'
FORMULA = 'Neg(Cs_Rank(Sub(Ts_MAD(If(Less(Returns, 0), Returns, 0), 60, 30), Ts_MAD(If(Greater(Returns, 0), Returns, 0), 60, 30))))'
ECONOMIC_HYPOTHESIS = 'Greater dispersion among negative sessions than positive sessions reveals heterogeneous downside shocks and a risk asymmetry missed by average semivariance.'
ECONOMIC_FAMILY = 'volatility_asymmetry'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['volatility_asymmetry']
INTERNAL_SUB_BATCH = 3
