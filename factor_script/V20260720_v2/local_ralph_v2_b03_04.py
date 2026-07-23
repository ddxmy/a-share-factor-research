FACTOR_NAME = "Location_Volume_Confirmation"
FORMULA = "Cs_Rank(Ts_Correlation(Div(Sub(Mul(2, close), Add(high, low)), Add(Sub(high, low), 0.001)), Div(volume, Ts_Mean(volume, 20, 10)), 20, 10))"
ECONOMIC_HYPOTHESIS = "Persistent correlation between close location and abnormal volume captures whether directional closing pressure is participation-confirmed."
TARGET_PATTERNS = ["price_volume_turnover_divergence"]

