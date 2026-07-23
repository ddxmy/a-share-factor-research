FACTOR_NAME = "Robust_Median_Drift"
FORMULA = "Cs_Rank(Div(Ts_Median(Returns, 60, 30), Add(Ts_MAD(Returns, 60, 30), 0.001)))"
ECONOMIC_HYPOTHESIS = "Median daily drift relative to median absolute dispersion provides a robust, continuous, low-turnover trend estimate."
TARGET_PATTERNS = ["trend_quality_path_efficiency"]

