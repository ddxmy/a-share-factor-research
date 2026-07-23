FACTOR_NAME = "Robust_Signed_Volume_Persistence"
FORMULA = "Cs_Rank(Ts_Median(Mul(Sign(Sub(close, open)), Div(volume, Ts_Mean(volume, 20, 10))), 20, 10))"
ECONOMIC_HYPOTHESIS = "The median signed abnormal-volume impulse measures robust accumulation while suppressing isolated volume spikes."
TARGET_PATTERNS = ["signed_volume_accumulation"]

