FACTOR_NAME = "Volume_Weighted_Short_Reversal"
FORMULA = "Neg(Cs_Rank(Mul(Ts_Return(close, 3), Div(volume, Ts_Mean(volume, 20, 10)))))"
ECONOMIC_HYPOTHESIS = "Very short price moves supported by abnormal volume contain transitory pressure and should reverse cross-sectionally."
TARGET_PATTERNS = ["price_pressure_reversal"]

