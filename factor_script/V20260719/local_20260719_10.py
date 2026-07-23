"""Momentum scaled by short-versus-long volatility compression."""

FACTOR_NAME = "local_20260719_10"
FACTOR_TYPE = "T-1_factor"
FORMULA = "Cs_Rank(Mul(Ts_Return(close, 10), Inverse(Add(Volatility_Ratio(5, 20), 0.1))))"
ECONOMIC_HYPOTHESIS = "A directional move with compressed recent volatility may represent orderly information diffusion rather than a noisy jump."
TARGET_PATTERNS = "VolatilityScaledMomentum,VolatilityCompression"
