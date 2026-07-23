"""Sealed candidate from local_ralph_20260722_v4, Pack 02."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 2
CANDIDATE_ID = 'local_ralph_v4_p02_039'
FACTOR_NAME = 'Opening_Auction_VWAP_Pressure_Reversal'
FORMULA = 'Neg(Cs_Rank(Mul(Div(Sub(open, pre_close), pre_close), Div(Sub(open, vwap), vwap))))'
ECONOMIC_HYPOTHESIS = "When the overnight gap and the opening price's displacement from session VWAP reinforce each other, opening-auction pressure is likely overextended and mean-reverting."
ECONOMIC_FAMILY = 'price_pressure_reversal'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['price_pressure_reversal', 'overnight_intraday_decomposition']
INTERNAL_SUB_BATCH = 4
