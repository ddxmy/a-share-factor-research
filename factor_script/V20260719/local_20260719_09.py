"""Medium-horizon momentum confirmed by recent volume."""

FACTOR_NAME = "local_20260719_09"
FACTOR_TYPE = "T-1_factor"
FORMULA = "Cs_Rank(Mul(Ts_Return(close, 20), Div(Ts_Mean(volume, 5), Ts_Mean(volume, 20))))"
ECONOMIC_HYPOTHESIS = "Price trends receiving fresh participation are more likely to reflect information diffusion than stale drift."
TARGET_PATTERNS = "VolumeConfirmedMomentum"
