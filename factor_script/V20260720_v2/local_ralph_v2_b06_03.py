FACTOR_NAME = "Continuous_Slope_MAD_Efficiency"
FORMULA = "Cs_Rank(Div(Slope(Log(close), 20), Add(Ts_MAD(Log(close), 20, 10), 0.001)))"
ECONOMIC_HYPOTHESIS = "Log-price slope normalized by path dispersion is a continuous measure of directional efficiency without discrete-value degeneration."
TARGET_PATTERNS = ["trend_quality_path_efficiency"]

