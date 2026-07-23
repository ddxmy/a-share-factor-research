FACTOR_NAME = "Return_Volatility_Leverage_Beta"
FORMULA = "Neg(Cs_Rank(Ts_Beta(Ts_Delta(Ts_Std(Returns, 20, 10), 1), Returns, 60, 30)))"
ECONOMIC_HYPOTHESIS = "The beta of changes in realized volatility to returns captures the leverage-like asymmetry of volatility expansion after losses."
TARGET_PATTERNS = ["conditional_regimes"]

