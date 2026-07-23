"""Sealed candidate from local_ralph_20260722_v4, Pack 01."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 1
CANDIDATE_ID = 'local_ralph_v4_p01_023'
FACTOR_NAME = 'Attention_Amplified_Volatility_Shock'
FORMULA = 'Neg(Cs_Rank(Mul(Div(Ts_Std(Returns, 10, 5), Add(Ts_Std(Returns, 40, 20), 0.001)), Ts_ZScore(Log(amt), 40, 20))))'
ECONOMIC_HYPOTHESIS = 'Short-term volatility expansion accompanied by abnormal trading amount signals attention-driven instability rather than quiet information diffusion.'
ECONOMIC_FAMILY = 'volatility_asymmetry'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['volatility_asymmetry', 'liquidity_amount_shocks']
INTERNAL_SUB_BATCH = 3
