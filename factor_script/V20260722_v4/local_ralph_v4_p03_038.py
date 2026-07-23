"""Sealed candidate from local_ralph_20260722_v4, Pack 03."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 3
CANDIDATE_ID = 'local_ralph_v4_p03_038'
FACTOR_NAME = 'Turnover_Participation_Regime_Switch'
FORMULA = 'If(Greater(Ts_Mean(turn, 10, 5), Ts_Mean(turn, 30, 15)), Cs_Rank(Ts_Mean(Mul(Sign(Returns), Div(volume, Add(Ts_Mean(volume, 20, 10), 1))), 20, 10)), Cs_Rank(Div(Ts_Return(close, 20), Add(Ts_Sum(Abs(Returns), 20, 10), 0.001))))'
ECONOMIC_HYPOTHESIS = 'Rising-turnover regimes emphasize signed participation, while quieter regimes emphasize price-path efficiency, adapting mechanism by observable liquidity state.'
ECONOMIC_FAMILY = 'conditional_regimes'
DATA_DOMAIN = 'turnover_size_liquidity'
TARGET_PATTERNS = ['conditional_regimes', 'signed_volume_accumulation', 'trend_quality_path_efficiency']
INTERNAL_SUB_BATCH = 4
