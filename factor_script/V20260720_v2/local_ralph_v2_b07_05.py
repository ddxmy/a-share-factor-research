FACTOR_NAME = "Risk_Scaled_Downside_Shortfall"
FORMULA = "Cs_Rank(Div(Ts_Mean(If(Less(Returns, Ts_Quantile(Returns, 60, 0.1, 30)), Returns, 0), 60, 30), Add(Ts_MAD(Returns, 60, 30), 0.001)))"
ECONOMIC_HYPOTHESIS = "Downside expected shortfall normalized by typical return dispersion separates persistent tail damage from generally volatile stocks."
TARGET_PATTERNS = ["return_tails_skewness"]

