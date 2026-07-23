"""Intraday return relative to the preceding overnight gap."""

FACTOR_NAME = "local_20260719_02"
FACTOR_TYPE = "T-1_factor"
FORMULA = "Cs_Rank(Sub(Div(Sub(close, open), open), Div(Sub(open, pre_close), pre_close)))"
ECONOMIC_HYPOTHESIS = "A close-to-open disagreement separates persistent information from temporary overnight price pressure."
TARGET_PATTERNS = "OvernightIntradayDecomposition"
