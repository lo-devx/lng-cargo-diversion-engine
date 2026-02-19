import pytest
from engine.validation import validate_config

# Valid config fixture
VALID_CONFIG = {
    "DECISION_BUFFER_USD": 250000,
    "OPS_BUFFER_USD": 150000,
    "BASIS_ADJUSTMENT": 0.05,
    "COVERAGE_PCT": 0.80,
    "TTF_LOT_MMBTU": 10000,
    "JKM_LOT_MMBTU": 10000,
    "STRESS_SPREAD_USD": 1.0,
    "STRESS_FREIGHT_USD_PER_DAY": 20000,
    "STRESS_EUA_USD": 10.0,
}

def test_validate_config_ok():
    validate_config(VALID_CONFIG)
   
def test_validate_config_rejects_percent_basis():
    cfg = {**VALID_CONFIG, "BASIS_ADJUSTMENT": 5.0}  # Wrong: should be 0.05
    with pytest.raises(ValueError):
        validate_config(cfg)