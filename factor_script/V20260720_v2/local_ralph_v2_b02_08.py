FACTOR_NAME = "Signed_Flow_Covariance"
FORMULA = "Cs_Rank(Ts_Covariance(Sign(Returns), Div(volume, Ts_Mean(volume, 20, 10)), 20, 10))"
ECONOMIC_HYPOTHESIS = "Positive covariance between return sign and abnormal volume distinguishes systematic accumulation from noisy turnover."
TARGET_PATTERNS = ["signed_volume_accumulation"]

