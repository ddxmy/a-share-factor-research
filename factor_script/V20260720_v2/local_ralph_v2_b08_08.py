FACTOR_NAME = "VWAP_Amount_Impulse_Covariance"
FORMULA = "Neg(Cs_Rank(Ts_Covariance(Div(Sub(close, vwap), vwap), Ts_Delta(Log(amt), 5), 60, 30)))"
ECONOMIC_HYPOTHESIS = "Covariance between VWAP displacement and medium-horizon amount impulses captures persistent price-participation disagreement."
TARGET_PATTERNS = ["price_volume_turnover_divergence"]

