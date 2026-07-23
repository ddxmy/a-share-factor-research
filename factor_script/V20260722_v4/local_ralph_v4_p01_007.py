"""Sealed candidate from local_ralph_20260722_v4, Pack 01."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 1
CANDIDATE_ID = 'local_ralph_v4_p01_007'
FACTOR_NAME = 'Sales_Multiple_Median_Dislocation'
FORMULA = 'Neg(Cs_Rank(Div(Sub(Log(Add(ps_ttm, 1)), Ts_Median(Log(Add(ps_ttm, 1)), 60, 30)), Add(Ts_MAD(Log(Add(ps_ttm, 1)), 60, 30), 0.001))))'
ECONOMIC_HYPOTHESIS = 'Robustly standardized sales-multiple dislocations isolate unusually cheap revenue franchises while limiting sensitivity to episodic valuation spikes.'
ECONOMIC_FAMILY = 'valuation_history_reversion'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['valuation_history_reversion']
INTERNAL_SUB_BATCH = 1
