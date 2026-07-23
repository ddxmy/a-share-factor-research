FACTOR_NAME = "Downside_Upside_Volatility_Beta"
FORMULA = "Neg(Cs_Rank(Ts_Beta(If(Less(Returns, 0), Abs(Returns), 0), If(Greater(Returns, 0), Returns, 0), 20, 10)))"
ECONOMIC_HYPOTHESIS = "A strong dependence of downside magnitudes on upside variation signals asymmetric fragility and unfavorable future returns."
TARGET_PATTERNS = ["volatility_asymmetry"]

