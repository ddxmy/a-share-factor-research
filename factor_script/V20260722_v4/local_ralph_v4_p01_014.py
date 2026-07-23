"""Sealed candidate from local_ralph_20260722_v4, Pack 01."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 1
CANDIDATE_ID = 'local_ralph_v4_p01_014'
FACTOR_NAME = 'Valuation_Turnover_Rerating_Decoupling'
FORMULA = 'Neg(Cs_Rank(Ts_Correlation(Ts_Delta(Log(Add(Abs(pe_ttm), 1)), 1), Ts_Return(turn, 1), 60, 30)))'
ECONOMIC_HYPOTHESIS = 'Persistent decoupling between earnings-multiple changes and turnover changes can expose valuation moves unsupported by broad trading participation and prone to correction.'
ECONOMIC_FAMILY = 'valuation_market_interaction'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['price_volume_turnover_divergence']
INTERNAL_SUB_BATCH = 2
