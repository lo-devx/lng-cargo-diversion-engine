from typing import Dict, Any

def validate_config(cfg: Dict[str, Any]) -> None:
   required = [
       "DECISION_BUFFER_USD",
       "OPS_BUFFER_USD",
       "BASIS_ADJUSTMENT",
       "COVERAGE_PCT",
       "TTF_LOT_MMBTU",
       "JKM_LOT_MMBTU",
       "STRESS_SPREAD_USD",
       "STRESS_FREIGHT_USD_PER_DAY",
       "STRESS_EUA_USD",
   ]
   missing = [k for k in required if k not in cfg]
   if missing:
       raise KeyError(f"Missing config keys: {missing}")
   
# numeric checks
   basis = float(cfg["BASIS_ADJUSTMENT"])
   cov = float(cfg["COVERAGE_PCT"])
   if not (0.0 <= basis <= 1.0):
       raise ValueError("BASIS_ADJUSTMENT must be in [0,1]")
   if not (0.0 <= cov <= 1.0):
       raise ValueError("COVERAGE_PCT must be in [0,1]")
   for k in ["DECISION_BUFFER_USD", "OPS_BUFFER_USD", "TTF_LOT_MMBTU", "JKM_LOT_MMBTU"]:
       if float(cfg[k]) <= 0:
           raise ValueError(f"{k} must be > 0")
   for k in ["STRESS_SPREAD_USD", "STRESS_FREIGHT_USD_PER_DAY", "STRESS_EUA_USD"]:
       if float(cfg[k]) < 0:
           raise ValueError(f"{k} must be >= 0")