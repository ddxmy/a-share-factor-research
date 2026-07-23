"""Short-versus-long volume participation shock."""

FACTOR_NAME = "local_20260719_29"
FACTOR_TYPE = "T-1_factor"
FORMULA = "Neg(Cs_Rank(Div(Ts_Mean(volume, 5, 3), Add(Ts_Mean(volume, 60, 30), 1))))"
ECONOMIC_HYPOTHESIS = "A burst of participation relative to a stable baseline can represent crowded attention and temporary demand."
TARGET_PATTERNS = "VolumeParticipationShock"
