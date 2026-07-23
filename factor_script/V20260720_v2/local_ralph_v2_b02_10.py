FACTOR_NAME = "Volatility_Regime_Pressure_Reversal"
FORMULA = "Neg(Cs_Rank(If(Greater(Volatility_Ratio(5, 20), 1), Mul(Ts_Return(close, 3), Div(volume, Ts_Mean(volume, 20, 10))), Ts_Return(close, 20))))"
ECONOMIC_HYPOTHESIS = "Short-horizon volume pressure should reverse in expanding-volatility regimes, while calmer regimes carry slower trend information."
TARGET_PATTERNS = ["conditional_regimes"]

