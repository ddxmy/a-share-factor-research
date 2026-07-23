FACTOR_NAME = "Signed_Multiscale_Path_Roughness"
FORMULA = "Cs_Rank(Mul(Sign(Ts_Return(close, 60)), Div(Ts_Sum(Abs(Returns), 60, 30), Add(Ts_Sum(Abs(Ts_Return(close, 5)), 60, 30), 0.001))))"
ECONOMIC_HYPOTHESIS = "Directional sign combined with fine-to-coarse total variation measures nonlinear path roughness across sampling scales."
TARGET_PATTERNS = ["trend_quality_path_efficiency"]

