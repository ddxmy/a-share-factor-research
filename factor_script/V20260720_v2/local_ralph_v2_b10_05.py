FACTOR_NAME = "Direction_Change_Adjusted_Path"
FORMULA = "Cs_Rank(Div(Ts_Return(close, 60), Add(Ts_Mean(Mul(Abs(Returns), Abs(Sub(Sign(Returns), Sign(Ts_Delay(Returns, 1))))), 60, 30), 0.001)))"
ECONOMIC_HYPOTHESIS = "Net long-horizon displacement relative to magnitude-weighted direction changes penalizes oscillatory paths continuously."
TARGET_PATTERNS = ["trend_quality_path_efficiency"]

