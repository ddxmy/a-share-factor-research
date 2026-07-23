FACTOR_NAME = "Segmented_Slope_Acceleration"
FORMULA = "Cs_Rank(Sub(Slope(Log(close), 20), Ts_Delay(Slope(Log(close), 20), 20)))"
ECONOMIC_HYPOTHESIS = "Change between current and lagged non-overlapping log-price slopes measures second-order path acceleration."
TARGET_PATTERNS = ["trend_quality_path_efficiency"]

