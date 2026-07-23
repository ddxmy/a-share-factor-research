"""Sealed candidate from local_ralph_20260722_v4, Pack 01."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 1
CANDIDATE_ID = 'local_ralph_v4_p01_036'
FACTOR_NAME = 'Compressed_Regime_Short_Reversal'
FORMULA = 'Neg(Cs_Rank(If(Less(Volatility_Ratio(5, 40), 0.7), Ts_Return(close, 3), Mul(Ts_Return(close, 3), 0.5))))'
ECONOMIC_HYPOTHESIS = 'Short price pressure should reverse more cleanly in compressed volatility regimes, while the same move in expanding risk receives a reduced contrarian weight.'
ECONOMIC_FAMILY = 'conditional_regimes'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['conditional_regimes', 'price_pressure_reversal']
INTERNAL_SUB_BATCH = 4
