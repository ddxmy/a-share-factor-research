FACTOR_NAME = "VWAP_Attention_Pressure_Reversal"
FORMULA = "Neg(Cs_Rank(Mul(Div(Sub(close, vwap), vwap), Ts_ZScore(Log(amt), 20, 10))))"
ECONOMIC_HYPOTHESIS = "Price displacement from VWAP is most transitory when it occurs under unusually intense traded-amount attention."
TARGET_PATTERNS = ["price_pressure_reversal"]

