from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class MarketSnapshot:
   asof: str
   ttf_usd_mmbtu: float
   jkm_usd_mmbtu: float
   freight_usd_day: float
   fuel_usd_per_t: float
   eua_usd_per_tco2: float
   provenance: Dict[str, str]  # "proxy" or "real"
   
def get_market_snapshot(cfg: Dict[str, Any], asof: str = "latest") -> MarketSnapshot:
   """
   Offline/proxy snapshot
   (Swap this to a licensed market data without touching engine logic)
   """
   ttf = float(cfg["TTF_USD_MMBTU"])
   eua = float(cfg["EUA_USD_PER_TCO2"])
   
# Proxy JKM = TTF + premium (explicit)
   premium = float(cfg.get("JKM_PREMIUM_USD_PER_MMBTU", 0.0))
   jkm = float(cfg.get("JKM_USD_MMBTU", ttf + premium))
   
# Proxy freight = base * regime multiplier
   freight_base = float(cfg["FREIGHT_USD_DAY"])
   mult = float(cfg.get("FREIGHT_REGIME_MULTIPLIER", 1.0))
   freight = freight_base * mult
   fuel = float(cfg["FUEL_USD_PER_T"])
   prov = {
       "TTF": "proxy",
       "EUA": "proxy",
       "JKM": "proxy",
       "FREIGHT": "proxy",
       "FUEL": "proxy",
   }
   return MarketSnapshot(
       asof=asof,
       ttf_usd_mmbtu=ttf,
       jkm_usd_mmbtu=jkm,
       freight_usd_day=freight,
       fuel_usd_per_t=fuel,
       eua_usd_per_tco2=eua,
       provenance=prov,
   )
