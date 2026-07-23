FACTOR_NAME = "Signed_Variance_Covariance"
FORMULA = "Neg(Cs_Rank(Ts_Covariance(Sign(Returns), Power(Returns, 2), 20, 10)))"
ECONOMIC_HYPOTHESIS = "Covariance between return sign and squared return captures whether realized variance is concentrated on upside or downside days."
TARGET_PATTERNS = ["volatility_asymmetry"]

