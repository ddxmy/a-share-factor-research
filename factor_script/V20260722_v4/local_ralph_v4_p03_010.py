"""Sealed candidate from local_ralph_20260722_v4, Pack 03."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 3
CANDIDATE_ID = 'local_ralph_v4_p03_010'
FACTOR_NAME = 'Volatility_Expansion_Reversal_Regime'
FORMULA = 'If(Greater(Volatility_Ratio(5, 30), 1), Neg(Cs_Rank(Ts_Return(close, 3))), Cs_Rank(Div(Ts_Return(close, 20), Add(Ts_Sum(Abs(Returns), 20, 10), 0.001))))'
ECONOMIC_HYPOTHESIS = 'Short reversal is favored only during volatility expansion, while quieter states use path-efficient medium drift, separating two distinct price-formation regimes.'
ECONOMIC_FAMILY = 'conditional_regimes'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['conditional_regimes', 'price_pressure_reversal', 'trend_quality_path_efficiency']
INTERNAL_SUB_BATCH = 1
