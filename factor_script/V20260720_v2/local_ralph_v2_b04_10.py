FACTOR_NAME = "Fragility_Amplified_Short_Reversal"
FORMULA = "Neg(Cs_Rank(Mul(Div(Ts_Return(close, 3), Add(Ts_Mean(turn, 3, 2), 0.1)), Div(Ts_Mean(If(Less(Returns, 0), Abs(Returns), 0), 20, 10), Add(Ts_Mean(If(Greater(Returns, 0), Returns, 0), 20, 10), 0.001)))))"
ECONOMIC_HYPOTHESIS = "Turnover-normalized short pressure should reverse most strongly when downside variation dominates upside variation."
TARGET_PATTERNS = ["conditional_regimes"]

