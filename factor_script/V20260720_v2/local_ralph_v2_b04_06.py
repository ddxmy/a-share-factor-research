FACTOR_NAME = "Lower_Upper_Wick_Beta"
FORMULA = "Cs_Rank(Ts_Beta(Sub(Min(open, close), low), Sub(high, Max(open, close)), 20, 10))"
ECONOMIC_HYPOTHESIS = "Rolling beta of lower-wick pressure to upper-wick pressure captures persistent asymmetry in rejection dynamics."
TARGET_PATTERNS = ["volatility_asymmetry"]

