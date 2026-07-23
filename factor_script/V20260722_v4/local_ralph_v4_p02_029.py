"""Sealed candidate from local_ralph_20260722_v4, Pack 02."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 2
CANDIDATE_ID = 'local_ralph_v4_p02_029'
FACTOR_NAME = 'Volume_Response_Gain_Loss_Beta_Gap'
FORMULA = 'Cs_Rank(Sub(Ts_Beta(Ts_Return(volume, 1), If(Greater(Returns, 0), Returns, 0), 40, 20), Ts_Beta(Ts_Return(volume, 1), If(Less(Returns, 0), Abs(Returns), 0), 40, 20)))'
ECONOMIC_HYPOTHESIS = 'Asymmetric volume elasticity to gains versus losses reveals whether participation confirms upside or disproportionately reacts to downside stress.'
ECONOMIC_FAMILY = 'price_volume_turnover_divergence'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['price_volume_turnover_divergence']
INTERNAL_SUB_BATCH = 3
