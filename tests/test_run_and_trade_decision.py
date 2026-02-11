import pandas as pd
from engine.run import run_trade_decision

def test_run_trade_decision_golden_case_runs():
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
       "CO2_factor_VLSFO_tCO2_per_t_fuel": 3.114,
       "CO2_factor_LNG_tCO2_per_t_fuel": 3.114,
   }
   pack = run_trade_decision(
       routes=routes,
       vessels=vessels,
       carbon_params=carbon_params,
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
       basis_haircut_pct=0.05,
       ops_buffer_usd=150000,
       decision_buffer_usd=250000,
       coverage_pct=0.80,
   )
   assert "europe" in pack and "asia" in pack and "decision" in pack
   assert pack["decision"]["delta_raw_usd"] == pack["asia"]["netback_usd"] - pack["europe"]["netback_usd"]
   assert pack["decision"]["hedge_energy_mmbtu"] > 0
   assert len(pack["hedge_legs"]) == 2