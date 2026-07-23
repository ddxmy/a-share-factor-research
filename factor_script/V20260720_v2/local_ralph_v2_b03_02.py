FACTOR_NAME = "Turnover_Normalized_Short_Pressure"
FORMULA = "Neg(Cs_Rank(Div(Ts_Return(close, 3), Add(Ts_Mean(turn, 3, 2), 0.1))))"
ECONOMIC_HYPOTHESIS = "Short price moves achieved with little turnover represent concentrated pressure and should reverse more strongly."
TARGET_PATTERNS = ["price_pressure_reversal"]

