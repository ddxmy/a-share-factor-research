FACTOR_NAME = "Persistent_VWAP_Displacement"
FORMULA = "Neg(Cs_Rank(Ts_Median(Div(Sub(close, vwap), vwap), 10, 5)))"
ECONOMIC_HYPOTHESIS = "A median close-to-VWAP displacement identifies sustained anchoring pressure rather than a one-day shock."
TARGET_PATTERNS = ["price_pressure_reversal"]

