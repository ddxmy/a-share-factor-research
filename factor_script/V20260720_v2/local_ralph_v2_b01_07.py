FACTOR_NAME = "Lower_Upper_Wick_Asymmetry"
FORMULA = "Cs_Rank(Ts_Mean(Div(Sub(Sub(Min(open, close), low), Sub(high, Max(open, close))), Add(Sub(high, low), 0.001)), 20, 10))"
ECONOMIC_HYPOTHESIS = "Persistent lower-wick dominance over upper wicks captures asymmetric rejection of low prices and buying resilience."
TARGET_PATTERNS = ["volatility_asymmetry"]

