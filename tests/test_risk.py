"""
Manual test script to understand how risk/stress testing works

What this does:
- Loads real data and fetches live market prices from Yahoo Finance
- Calculates base netbacks and makes a decision
- Runs stress scenarios (spread collapse, freight spike, EUA spike, combined adverse)
- Shows P&L impact and decision flips for each scenario
- Displays detailed output so you can see what's happening step-by-step

Run from project root: python tests/test_risk.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.data_loader import load_routes, load_vessels, load_carbon_params, load_config
from engine.market_data import get_market_snapshot
from engine.netback import NetbackCalculator
from engine.decision import decide_and_size
from engine.risk import RiskAnalyzer
from engine.reports import save_stress_csv

# Load data
print("Loading data...")
routes = load_routes()
vessels = load_vessels()
carbon_params = load_carbon_params()
config = load_config()

# Get market snapshot
print("\nFetching market prices...")
market = get_market_snapshot(config)
print(f"TTF: ${market.ttf_usd_mmbtu:.2f}, EUA: ${market.eua_usd_per_tco2:.2f}")

# Setup netback calculator
calculator = NetbackCalculator(routes, vessels, carbon_params)

# Calculate base netbacks
print("\nCalculating base case netbacks...")
europe_nb, asia_nb = calculator.compare_netbacks(
    load_port="US_Gulf",
    europe_port="Rotterdam",
    asia_port="Tokyo",
    vessel_class="TFDE",
    cargo_capacity_m3=174000,
    ttf_price=market.ttf_usd_mmbtu,
    jkm_price=market.jkm_usd_mmbtu,
    freight_rate_usd_day=market.freight_usd_day,
    fuel_price_usd_t=market.fuel_usd_per_t,
    eua_price_usd_t=market.eua_usd_per_tco2
)

print(f"Europe netback: ${europe_nb.netback_usd:,.0f}")
print(f"Asia netback:   ${asia_nb.netback_usd:,.0f}")

# Make base decision
base_decision = decide_and_size(
    europe_netback_usd=europe_nb.netback_usd,
    asia_netback_usd=asia_nb.netback_usd,
    hedge_energy_mmbtu=asia_nb.delivered_energy_mmbtu,
    basis_haircut_pct=float(config["BASIS_ADJUSTMENT"]),
    ops_buffer_usd=float(config["OPS_BUFFER_USD"]),
    decision_buffer_usd=float(config["DECISION_BUFFER_USD"])
)

print(f"\nBase Decision: {base_decision.decision}")
print(f"Adjusted delta: ${base_decision.delta_netback_adj_usd:,.0f}")

# Setup risk analyzer
print("\n" + "="*60)
print("STRESS TESTING")
print("="*60)

risk_analyzer = RiskAnalyzer(
    netback_calculator=calculator,
    stress_spread_usd=float(config["STRESS_SPREAD_USD"]),
    stress_freight_usd_per_day=float(config["STRESS_FREIGHT_USD_PER_DAY"]),
    stress_eua_usd=float(config["STRESS_EUA_USD"]),
    basis_haircut_pct=float(config["BASIS_ADJUSTMENT"]),
    ops_buffer_usd=float(config["OPS_BUFFER_USD"]),
    decision_buffer_usd=float(config["DECISION_BUFFER_USD"])
)

# Run stress tests
risk_pack = risk_analyzer.run_stress_test(
    base_result=base_decision,
    load_port="US_Gulf",
    europe_port="Rotterdam",
    asia_port="Tokyo",
    vessel_class="TFDE",
    cargo_capacity_m3=174000,
    ttf_price=market.ttf_usd_mmbtu,
    jkm_price=market.jkm_usd_mmbtu,
    freight_rate_usd_day=market.freight_usd_day,
    fuel_price_usd_t=market.fuel_usd_per_t,
    eua_price_usd_t=market.eua_usd_per_tco2
)

# Display stress results
print(f"\nWorst case P&L impact: ${risk_pack.worst_case_pnl_impact:,.0f}")
print(f"Scenarios causing decision flip: {risk_pack.scenarios_causing_flip}\n")

print("-"*60)
print(f"{'Scenario':<25} {'P&L Impact':>15} {'Decision':>10} {'Flipped?':>8}")
print("-"*60)

for result in risk_pack.stress_results:
    flipped = "YES" if result.decision_change else "NO"
    print(f"{result.scenario.name:<25} ${result.pnl_impact_usd:>14,.0f} {result.stressed_decision:>10} {flipped:>8}")

print("="*60)

# Save stress pack to CSV
stress_rows = []
for result in risk_pack.stress_results:
    stress_rows.append({
        "scenario": result.scenario.name,
        "spread_shock_usd": result.scenario.spread_shock_usd,
        "freight_shock_usd_day": result.scenario.freight_shock_usd_day,
        "eua_shock_usd": result.scenario.eua_shock_usd,
        "base_decision": result.base_decision,
        "stressed_decision": result.stressed_decision,
        "decision_flipped": result.decision_change,
        "pnl_impact_usd": result.pnl_impact_usd,
        "base_delta_adj_usd": result.base_delta_netback_adj,
        "stressed_delta_adj_usd": result.stressed_delta_netback_adj
    })

csv_path = save_stress_csv(stress_rows)
print(f"\n✓ Saved stress pack: {csv_path}")
