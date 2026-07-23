FACTOR_NAME = "Directional_Path_Consistency"
FORMULA = "Cs_Rank(Mul(Sign(Ts_Return(close, 20)), Abs(Ts_Mean(Sign(Returns), 20, 10))))"
ECONOMIC_HYPOTHESIS = "Endpoint direction reinforced by the fraction of same-sign daily moves measures orderly, low-noise trend quality."
TARGET_PATTERNS = ["trend_quality_path_efficiency"]

