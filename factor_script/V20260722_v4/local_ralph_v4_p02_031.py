"""Sealed candidate from local_ralph_20260722_v4, Pack 02."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 2
CANDIDATE_ID = 'local_ralph_v4_p02_031'
FACTOR_NAME = 'Book_Multiple_Robust_IQR_Dislocation'
FORMULA = 'Neg(Cs_Rank(Div(Sub(Log(Add(pb, 1)), Ts_Median(Log(Add(pb, 1)), 100, 50)), Add(Sub(Ts_Quantile(Log(Add(pb, 1)), 100, 0.75, 50), Ts_Quantile(Log(Add(pb, 1)), 100, 0.25, 50)), 0.001))))'
ECONOMIC_HYPOTHESIS = 'PB displacement normalized by its own interquartile range identifies robust historical cheapness without relying on standard deviation or earnings coverage.'
ECONOMIC_FAMILY = 'valuation_history_reversion'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['valuation_history_reversion']
INTERNAL_SUB_BATCH = 4
