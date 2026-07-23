"""Sealed candidate from local_ralph_20260722_v4, Pack 02."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 2
CANDIDATE_ID = 'local_ralph_v4_p02_013'
FACTOR_NAME = 'Book_Discount_With_Range_Recovery'
FORMULA = 'Cs_Rank(Mul(Neg(Ts_Rank(Log(Add(pb, 1)), 100, 50)), Div(Sub(close, Ts_Min(low, 60, 30)), Add(Sub(Ts_Max(high, 60, 30), Ts_Min(low, 60, 30)), 0.001))))'
ECONOMIC_HYPOTHESIS = 'A historical PB discount becomes more actionable when price has begun recovering within its medium-term range, combining valuation with non-extreme confirmation.'
ECONOMIC_FAMILY = 'valuation_market_interaction'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['valuation_history_reversion', 'range_location_anchoring']
INTERNAL_SUB_BATCH = 2
