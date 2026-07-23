FACTOR_NAME = "Drawdown_Adjusted_Drift"
FORMULA = "Cs_Rank(Sub(Ts_Return(close, 20), Div(Sub(Ts_Max(high, 20, 10), close), Add(Ts_Max(high, 20, 10), 0.001))))"
ECONOMIC_HYPOTHESIS = "Medium-horizon drift penalized by current distance below the recent high distinguishes sustained trends from unresolved drawdowns."
TARGET_PATTERNS = ["trend_quality_path_efficiency"]

