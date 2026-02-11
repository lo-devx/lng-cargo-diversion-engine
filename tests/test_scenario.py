#run test with: 'pytest tests/test_scenario.py -s'

import pandas as pd
import json
from pathlib import Path
from engine.netback import NetbackCalculator

# Load prices from the notebook's last market snapshot
_snapshot_path = Path(__file__).parent.parent / "data" / "market_snapshot.json"
if _snapshot_path.exists():
    with open(_snapshot_path) as f:
        _snapshot = json.load(f)
    _ttf = _snapshot["ttf_price"]
    _jkm = _snapshot["jkm_price"]
    _freight = _snapshot["freight_rate"]
    _fuel = _snapshot["fuel_price"]
    _eua = _snapshot["eua_price"]
else:
    # Fallback if snapshot doesn't exist yet
    _ttf = 35.69
    _jkm = 38.44
    _freight = 85000
    _fuel = 583
    _eua = 74.40

GOLDEN_INPUTS = {

    "ttf_price": _ttf,

    "jkm_price": _jkm,

    "freight_rate": _freight,

    "fuel_price": _fuel,

    "eua_price": _eua,

    "cargo_capacity_m3": 174000,

    "laden_speed_kn": 19.5,

    "boil_off_pct_per_day": 0.10,

    "fuel_consumption_tpd": 130,

    "distance_europe_nm": 5000,

    "distance_asia_nm": 9500,

    # constants

    "lng_density_t_per_m3": 0.45,

    "mmbtu_per_tonne": 52.0,

    "co2_factor": 3.114,

    # decision knobs 

    "basis_adjustment_pct": 5.0,

    "decision_threshold_usd": 500000,

    "contract_size_mmbtu": 10000,

}

def _approx(a, b, rel=1e-3, abs_=1.0):
   return abs(a - b) <= max(abs_, rel * max(abs(a), abs(b)))

def test_golden_case_netbacks_match_notebook_shape():
   """
   Golden scenario:
     TTF 35.69, JKM 38.44, freight 85k/day, fuel 583, EUA 74.40
     TFDE 174k m3, speed 19.5kn, BOG 0.10%/day, fuel 130 t/day
     distances: EU 5000nm, Asia 9500nm
   """
   # Build input tables (contracts)
   routes = pd.DataFrame(
       [
           {"load_port": "US_Gulf", "discharge_port": "Rotterdam", "distance_nm": 5000},
           {"load_port": "US_Gulf", "discharge_port": "Tokyo", "distance_nm": 9500},
       ]
   )
   vessels = pd.DataFrame(
       [
           {
               "vessel_class": "TFDE",
               "cargo_capacity_m3": 174000,
               "laden_speed_kn": 19.5,
               "ballast_speed_kn": 19.5,
               "boil_off_pct_per_day": 0.10,
               "fuel_consumption_tpd_laden": 130,
               "fuel_consumption_tpd_ballast": 130,
           }
       ]
   )
   carbon_params = {
       # match your notebook CO2_FACTOR
       "CO2_factor_VLSFO_tCO2_per_t_fuel": 3.114,
       "CO2_factor_LNG_tCO2_per_t_fuel": 3.114,
   }
   calc = NetbackCalculator(routes=routes, vessels=vessels, carbon_params=carbon_params)
   europe, asia = calc.compare_netbacks(
       load_port="US_Gulf",
       europe_port="Rotterdam",
       asia_port="Tokyo",
       vessel_class="TFDE",
       cargo_capacity_m3=174000,
       ttf_price=35.69,
       jkm_price=38.44,
       freight_rate_usd_day=85000,
       fuel_price_usd_t=583,
       eua_price_usd_t=74.40,
   )
   # Assert key physics are consistent with notebook outputs 
   # Voyage days: notebook printed =10.7 and =20.3
   print(f"\n✓ Europe voyage days: {europe.voyage_details.voyage_days:.2f} (expected ~10.7)")
   print(f"✓ Asia voyage days: {asia.voyage_details.voyage_days:.2f} (expected ~20.3)")
   assert _approx(europe.voyage_details.voyage_days, 10.7, rel=0, abs_=0.15)
   assert _approx(asia.voyage_details.voyage_days, 20.3, rel=0, abs_=0.15)
   
   # Boil off m3: notebook printed =1,859 and =3,532 (for those days)
   print(f"✓ Europe boil-off: {europe.voyage_details.boil_off_m3:,.0f} m³ (expected ~1,859)")
   print(f"✓ Asia boil-off: {asia.voyage_details.boil_off_m3:,.0f} m³ (expected ~3,532)")
   assert _approx(europe.voyage_details.boil_off_m3, 1859, rel=0, abs_=50)
   assert _approx(asia.voyage_details.boil_off_m3, 3532, rel=0, abs_=80)
   
   # Delivered energy order should hold
   print(f"✓ Europe delivered: {europe.delivered_energy_mmbtu:,.0f} MMBtu")
   print(f"✓ Asia delivered: {asia.delivered_energy_mmbtu:,.0f} MMBtu")
   assert europe.delivered_energy_mmbtu > asia.delivered_energy_mmbtu
   
   # Netbacks should be sensible
   print(f"✓ Europe netback: ${europe.netback_usd:,.0f}")
   print(f"✓ Asia netback: ${asia.netback_usd:,.0f}")
   assert asia.netback_usd > europe.netback_usd  # with JKM > TTF in this golden case
   
   # Uplift should be positive and material (not a tiny rounding diff)
   uplift = asia.netback_usd - europe.netback_usd
   print(f"✓ Uplift: ${uplift:,.0f} (must be >$100k)")
   assert uplift > 0
   assert uplift > 100000  # >$100k (catch obvious breaks)