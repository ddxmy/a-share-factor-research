FACTOR_NAME = "Extrema_Recency_Trend_Quality"
FORMULA = "Cs_Rank(Mul(Sign(Ts_Return(close, 20)), Sub(Ts_ArgMin(low, 20, 10), Ts_ArgMax(high, 20, 10))))"
ECONOMIC_HYPOTHESIS = "The ordering and recency of local highs and lows distinguish orderly directional trends from noisy displacement."
TARGET_PATTERNS = ["trend_quality_path_efficiency"]

