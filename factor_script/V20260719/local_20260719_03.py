"""Price-volume divergence measured by rolling return correlation."""

FACTOR_NAME = "local_20260719_03"
FACTOR_TYPE = "T-1_factor"
FORMULA = "Neg(Cs_Rank(Ts_Correlation(Returns, Ts_Return(volume, 1), 20, 10)))"
ECONOMIC_HYPOTHESIS = "Persistent positive price-volume co-movement can indicate crowded demand, while divergence can contain less crowded information."
TARGET_PATTERNS = "PriceVolumeDivergence"
