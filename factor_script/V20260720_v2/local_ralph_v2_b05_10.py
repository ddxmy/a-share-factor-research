FACTOR_NAME = "Volatility_Damped_Gap_Pressure"
FORMULA = "Neg(Cs_Rank(Mul(Ts_EMA(Div(Sub(open, pre_close), pre_close), 10, 5), Inverse(Add(Volatility_Ratio(5, 20), 0.5)))))"
ECONOMIC_HYPOTHESIS = "Persistent overnight pressure is more informative in stable volatility regimes; continuous damping avoids a high-churn regime switch."
TARGET_PATTERNS = ["conditional_regimes"]

