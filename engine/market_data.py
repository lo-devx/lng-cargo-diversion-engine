from dataclasses import dataclass
from typing import Dict, Any
import yfinance as yf
import pandas as pd
from datetime import datetime

# Objective: 
# Create snapshot of • TTF_USD_MMBTU (real from Yahoo) • EUA_USD_PER_TCO2 (real from Yahoo) • JKM_USD_MMBTU (proxy) • FREIGHT_USD_DAY (proxy) • FUEL_USD_PER_T (proxy/manual) • a provenance dict saying what's proxy vs real.


@dataclass
class MarketSnapshot:
   asof: str
   ttf_usd_mmbtu: float
   jkm_usd_mmbtu: float
   freight_usd_day: float
   fuel_usd_per_t: float
   eua_usd_per_tco2: float
   provenance: Dict[str, str]  # "proxy" or "real"
   
def _last_close(ticker: str) -> float:
   """
   Pull last available close from Yahoo Finance.
   Returns the most recent closing price for the given ticker.
   """
   data = yf.download(ticker, period="5d", progress=False)
   if data.empty:
       raise ValueError(f"No data returned for ticker {ticker}")
   close_series = data["Close"]
   return float(close_series.iloc[-1].item() if hasattr(close_series.iloc[-1], 'item') else close_series.iloc[-1])
   
def get_market_snapshot(cfg: Dict[str, Any], asof: str = "latest") -> MarketSnapshot:
   """
   Hybrid snapshot: real TTF and EUA from Yahoo Finance, proxy for JKM/freight/fuel
   """
   # Real data from Yahoo Finance
   ttf = _last_close("TTF=F")  # European natural gas futures
   eua = _last_close("CO2.L")  # Carbon allowances (EUA)
   
   # Generate timestamp if "latest"
   if asof == "latest":
       asof = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
   
# Proxy JKM = TTF + premium (explicit)
   premium = float(cfg.get("JKM_PREMIUM_USD_PER_MMBTU", 0.0))
   jkm = float(cfg.get("JKM_USD_MMBTU", ttf + premium))
   
# Proxy freight = base * regime multiplier
   freight_base = float(cfg["FREIGHT_USD_DAY"])
   mult = float(cfg.get("FREIGHT_REGIME_MULTIPLIER", 1.0))
   freight = freight_base * mult
   fuel = float(cfg["FUEL_USD_PER_T"])
   prov = {
       "TTF": "real",
       "EUA": "real",
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
