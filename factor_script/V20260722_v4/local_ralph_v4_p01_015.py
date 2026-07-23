"""Sealed candidate from local_ralph_20260722_v4, Pack 01."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 1
CANDIDATE_ID = 'local_ralph_v4_p01_015'
FACTOR_NAME = 'Cross_Multiple_History_Coherence'
FORMULA = 'Neg(Cs_Rank(Abs(Sub(Ts_ZScore(Log(Add(Abs(pe_ttm), 1)), 60, 30), Ts_ZScore(Log(Add(ps_ttm, 1)), 60, 30)))))'
ECONOMIC_HYPOTHESIS = 'Valuation moves jointly confirmed by earnings and sales multiples may be more reliable than isolated multiple shocks driven by a single accounting denominator.'
ECONOMIC_FAMILY = 'valuation_history_reversion'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['valuation_history_reversion']
INTERNAL_SUB_BATCH = 2
