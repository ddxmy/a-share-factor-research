FACTOR_NAME = "Extreme_Return_Recency_Asymmetry"
FORMULA = "Cs_Rank(Sub(Ts_ArgMax(Returns, 60, 30), Ts_ArgMin(Returns, 60, 30)))"
ECONOMIC_HYPOTHESIS = "The relative recency of extreme gains and losses captures tail-event anchoring without relying on a windowed skew transform."
TARGET_PATTERNS = ["return_tails_skewness"]

