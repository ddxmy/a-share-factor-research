"""Sealed candidate from local_ralph_20260722_v4, Pack 03."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 3
CANDIDATE_ID = 'local_ralph_v4_p03_020'
FACTOR_NAME = 'Price_Volume_Path_Efficiency_Gap'
FORMULA = 'Cs_Rank(Sub(Div(Ts_Return(close, 20), Add(Ts_Sum(Abs(Returns), 20, 10), 0.001)), Div(Ts_Return(volume, 20), Add(Ts_Sum(Abs(Ts_Return(volume, 1)), 20, 10), 0.001))))'
ECONOMIC_HYPOTHESIS = 'A smooth price trend unsupported by equally efficient volume migration identifies disagreement between price discovery and participation paths.'
ECONOMIC_FAMILY = 'price_volume_turnover_divergence'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['price_volume_turnover_divergence', 'trend_quality_path_efficiency']
INTERNAL_SUB_BATCH = 2
