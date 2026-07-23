"""Sealed candidate from local_ralph_20260722_v4, Pack 03."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 3
CANDIDATE_ID = 'local_ralph_v4_p03_037'
FACTOR_NAME = 'Book_Value_Regime_Trend_Switch'
FORMULA = 'If(Less(Cs_Rank(Ts_EMA(Log(Add(pb, 1)), 20, 10)), 0.35), Cs_Rank(Ts_Return(close, 20)), Neg(Cs_Rank(Ts_Return(close, 5))))'
ECONOMIC_HYPOTHESIS = 'Cheap PB regimes may support slower rerating trends, while non-cheap regimes are more vulnerable to short-horizon price-pressure reversal.'
ECONOMIC_FAMILY = 'conditional_regimes'
DATA_DOMAIN = 'valuation_dividend'
TARGET_PATTERNS = ['conditional_regimes', 'value_level_composite', 'price_pressure_reversal']
INTERNAL_SUB_BATCH = 4
