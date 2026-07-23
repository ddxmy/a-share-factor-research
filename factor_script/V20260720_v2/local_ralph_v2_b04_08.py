FACTOR_NAME = "Decay_Signed_Turnover_Balance"
FORMULA = "Cs_Rank(Div(Ts_DecayLinear(Mul(Sign(Returns), turn), 20, 10), Add(Ts_Mean(turn, 20, 10), 0.1)))"
ECONOMIC_HYPOTHESIS = "Recency-weighted signed turnover balance measures accumulation using ownership rotation rather than raw shares traded."
TARGET_PATTERNS = ["signed_volume_accumulation"]

