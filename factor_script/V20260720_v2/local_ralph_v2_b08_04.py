FACTOR_NAME = "Multiscale_Slope_Concordance"
FORMULA = "Cs_Rank(Mul(Sign(Slope(Log(close), 60)), Mul(Abs(Slope(Log(close), 10)), Abs(Slope(Log(close), 60)))))"
ECONOMIC_HYPOTHESIS = "Trend strength is credible when short and long log-price slopes carry substantial magnitude in the long-horizon direction."
TARGET_PATTERNS = ["trend_quality_path_efficiency"]

