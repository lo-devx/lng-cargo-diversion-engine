"""
Quick test script to see current TTF and EUA prices from Yahoo Finance

Run from project root: python tests/test_market_data.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.data_loader import load_config
from engine.market_data import get_market_snapshot

# Load config
config = load_config()

# Fetch market snapshot with real Yahoo Finance data
snapshot = get_market_snapshot(config)

print("\n" + "="*60)
print("CURRENT MARKET PRICES")
print("="*60)
print(f"TTF (European Gas):  ${snapshot.ttf_usd_mmbtu:.2f}/MMBtu  [{snapshot.provenance['TTF']}]")
print(f"EUA (Carbon):        ${snapshot.eua_usd_per_tco2:.2f}/tCO₂   [{snapshot.provenance['EUA']}]")
print(f"JKM (Asia Gas):      ${snapshot.jkm_usd_mmbtu:.2f}/MMBtu  [{snapshot.provenance['JKM']}]")
print(f"Freight:             ${snapshot.freight_usd_day:,.0f}/day [{snapshot.provenance['FREIGHT']}]")
print(f"Fuel:                ${snapshot.fuel_usd_per_t:.0f}/t    [{snapshot.provenance['FUEL']}]")
print("="*60)
print(f"As of: {snapshot.asof}\n")
