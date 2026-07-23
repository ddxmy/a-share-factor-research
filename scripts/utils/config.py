"""Configuration and constants for FactorMiner."""

import os

# Data paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
MEMORY_FILE = os.path.join(DATA_DIR, "experience_memory.json")
FACTOR_LIBRARY_FILE = os.path.join(DATA_DIR, "factor_library.json")
FACTOR_SCRIPT_DIR = os.path.join(PROJECT_ROOT, "factor_script")
TMP_DATA_DIR = os.path.join(PROJECT_ROOT, "tmp_data")
