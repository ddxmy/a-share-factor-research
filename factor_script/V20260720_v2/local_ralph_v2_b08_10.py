FACTOR_NAME = "Tail_Conditioned_Close_Anchor"
FORMULA = "Cs_Rank(Div(Ts_Median(Div(Sub(Mul(2, close), Add(high, low)), Add(Sub(high, low), 0.001)), 60, 30), Add(Abs(Ts_Mean(If(Less(Returns, Ts_Quantile(Returns, 60, 0.1, 30)), Returns, 0), 60, 30)), 0.01)))"
ECONOMIC_HYPOTHESIS = "Persistent close-location bias is more credible when scaled by the stock's downside expected-shortfall burden."
TARGET_PATTERNS = ["conditional_regimes"]

