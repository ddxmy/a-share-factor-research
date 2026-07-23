"""Sealed candidate from local_ralph_20260722_v4, Pack 01."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 1
CANDIDATE_ID = 'local_ralph_v4_p01_008'
FACTOR_NAME = 'Earnings_Book_Rerating_Divergence'
FORMULA = 'Neg(Cs_Rank(Sub(Ts_ZScore(Log(Add(Abs(pe_ttm), 1)), 60, 30), Ts_ZScore(Log(Add(pb, 1)), 60, 30))))'
ECONOMIC_HYPOTHESIS = "When the earnings multiple has compressed more than the book multiple relative to each stock's history, earnings pessimism may be overextended compared with balance-sheet valuation."
ECONOMIC_FAMILY = 'valuation_history_reversion'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['valuation_history_reversion']
INTERNAL_SUB_BATCH = 1
