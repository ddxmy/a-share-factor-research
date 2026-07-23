FACTOR_NAME = "Moving_Average_Path_Curvature"
FORMULA = "Cs_Rank(Div(Sub(Add(Ts_EMA(close, 10, 5), Ts_EMA(close, 60, 30)), Mul(2, Ts_EMA(close, 20, 10))), Add(Abs(Ts_EMA(close, 20, 10)), 0.001)))"
ECONOMIC_HYPOTHESIS = "Curvature across short, medium, and long exponential price paths captures nonlinear acceleration beyond a single trend slope."
TARGET_PATTERNS = ["trend_quality_path_efficiency"]

