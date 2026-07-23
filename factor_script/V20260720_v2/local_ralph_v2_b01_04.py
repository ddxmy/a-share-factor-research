FACTOR_NAME = "Excursion_Adjusted_Trend"
FORMULA = "Cs_Rank(Div(Ts_Return(close, 20), Add(Div(Sub(Ts_Max(high, 20, 10), Ts_Min(low, 20, 10)), Ts_Min(low, 20, 10)), 0.001)))"
ECONOMIC_HYPOTHESIS = "Net medium-horizon return relative to the full price excursion rewards directional trends and penalizes noisy paths."
TARGET_PATTERNS = ["trend_quality_path_efficiency"]

