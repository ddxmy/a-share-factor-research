"""Sealed candidate from local_ralph_20260722_v4, Pack 02."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 2
CANDIDATE_ID = 'local_ralph_v4_p02_040'
FACTOR_NAME = 'Price_Volume_Agreement_Regime_Switch'
FORMULA = 'If(Greater(Ts_Correlation(Returns, Ts_Return(volume, 1), 20, 10), 0), Neg(Cs_Rank(Ts_Return(close, 3))), Cs_Rank(Div(Ts_Return(close, 20), Add(Ts_Sum(Abs(Returns), 20, 10), 0.001))))'
ECONOMIC_HYPOTHESIS = 'Positive return-volume agreement marks crowding where short reversal is favored, whereas disagreement favors retaining only path-efficient medium-horizon trend exposure.'
ECONOMIC_FAMILY = 'conditional_regimes'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['conditional_regimes', 'price_volume_turnover_divergence']
INTERNAL_SUB_BATCH = 4
