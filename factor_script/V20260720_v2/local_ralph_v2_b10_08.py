FACTOR_NAME = "VWAP_Displacement_Amount_Beta"
FORMULA = "Neg(Cs_Rank(Ts_Beta(Ts_Delta(Div(Sub(close, vwap), vwap), 1), Ts_Delta(Log(amt), 1), 60, 30)))"
ECONOMIC_HYPOTHESIS = "Sensitivity of VWAP-displacement changes to amount impulses identifies price-anchor moves driven by participation shocks."
TARGET_PATTERNS = ["price_volume_turnover_divergence"]

