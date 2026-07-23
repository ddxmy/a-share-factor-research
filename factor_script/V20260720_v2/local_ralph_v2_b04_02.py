FACTOR_NAME = "Intraday_Pressure_Per_Turnover"
FORMULA = "Neg(Cs_Rank(Div(Div(Sub(close, open), open), Add(turn, 0.1))))"
ECONOMIC_HYPOTHESIS = "Intraday displacement achieved with limited turnover indicates concentrated order pressure and stronger subsequent reversal."
TARGET_PATTERNS = ["price_pressure_reversal"]

