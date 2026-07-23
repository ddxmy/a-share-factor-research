FACTOR_NAME = "Volume_Regime_Reversal_Trend_Switch"
FORMULA = "Cs_Rank(If(Greater(volume, Ts_Mean(volume, 20, 10)), Neg(Ts_Return(close, 3)), Div(Ts_Return(close, 20), Add(Ts_Sum(Abs(Returns), 20, 10), 0.000001))))"
ECONOMIC_HYPOTHESIS = "High-volume regimes favor reversal of short pressure, while ordinary-volume regimes reward efficient medium-horizon drift."
TARGET_PATTERNS = ["conditional_regimes"]

