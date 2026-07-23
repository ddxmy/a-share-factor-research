FACTOR_NAME = "Post_Range_Shock_Liquidity_Response"
FORMULA = "Cs_Rank(Ts_Mean(If(Greater(Ts_Delay(Div(Sub(high, low), pre_close), 1), Ts_Delay(Ts_Quantile(Div(Sub(high, low), pre_close), 60, 0.9, 30), 1)), Ts_Return(turn, 1), 0), 60, 30))"
ECONOMIC_HYPOTHESIS = "Turnover response following an extreme prior-day range measures whether liquidity providers return after volatility shocks."
TARGET_PATTERNS = ["liquidity_amount_shocks"]

