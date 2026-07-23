FACTOR_NAME = "Tail_Excess_Loss_Dispersion"
FORMULA = "Neg(Cs_Rank(Ts_Std(Max(Sub(Ts_Quantile(Returns, 60, 0.1, 30), Returns), 0), 60, 30)))"
ECONOMIC_HYPOTHESIS = "Dispersion of losses beyond the stock-specific downside quantile measures instability of tail severity."
TARGET_PATTERNS = ["return_tails_skewness"]

