FACTOR_NAME = "VWAP_Displacement_Persistence_Reversal"
FORMULA = "Neg(Cs_Rank(Ts_Correlation(Div(Sub(close, vwap), vwap), Ts_Delay(Div(Sub(close, vwap), vwap), 1), 20, 10)))"
ECONOMIC_HYPOTHESIS = "Serial persistence of close-to-VWAP displacement identifies crowded pressure around the trading anchor that should eventually reverse."
TARGET_PATTERNS = ["price_pressure_reversal"]

