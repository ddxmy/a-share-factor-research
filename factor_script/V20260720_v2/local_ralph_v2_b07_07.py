FACTOR_NAME = "Liquidity_Drought_Severity"
FORMULA = "Neg(Cs_Rank(Div(Ts_Mean(Max(Sub(Ts_Quantile(turn, 60, 0.2, 30), turn), 0), 60, 30), Add(Ts_Median(turn, 60, 30), 0.1))))"
ECONOMIC_HYPOTHESIS = "Average turnover shortfall below a stock's own lower participation quantile measures persistent liquidity drought severity."
TARGET_PATTERNS = ["liquidity_amount_shocks"]

