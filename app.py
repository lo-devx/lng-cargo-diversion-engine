"""
LNG Cargo Diversion Decision Engine 

Objective:
Determines whether to divert an LNG cargo from Europe (TTF) to Asia (JKM)
based on netback analysis, accounting for voyage costs, freight rates, and
carbon pricing. Outputs a trade decision (DIVERT/KEEP) and hedge recommendations.

Run with: python app.py 
"""

import argparse
from pathlib import Path
import json
from datetime import datetime

from engine.data_loader import load_routes, load_vessels, load_carbon_params, load_config
from engine.market_data import get_market_snapshot
from engine.run import run_trade_decision


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="LNG Cargo Diversion Decision Engine")
    parser.add_argument("--load-port", default="US_Gulf", help="Loading port")
    parser.add_argument("--europe-port", default="Rotterdam", help="Europe discharge port")
    parser.add_argument("--asia-port", default="Tokyo", help="Asia discharge port")
    parser.add_argument("--vessel-class", default="TFDE", help="Vessel class")
    parser.add_argument("--cargo-m3", type=float, default=174000, help="Cargo capacity in m3")
    
    # Decision parameter arguments
    parser.add_argument("--basis", type=float, help="Basis haircut 0-1 (e.g. 0.05)")
    parser.add_argument("--ops-buffer", type=float, help="Ops buffer in USD")
    parser.add_argument("--decision-buffer", type=float, help="Decision buffer in USD")
    parser.add_argument("--coverage", type=float, help="Coverage ratio 0-1 (e.g. 0.80)")
    parser.add_argument("--save", action="store_true", help="Save results to reports/")
    
    args = parser.parse_args()
    
    # Load static data and configuration
    routes = load_routes()
    vessels = load_vessels()
    carbon_params = load_carbon_params()
    config = load_config()
    
    # Get current market snapshot (proxy prices for now)
    market_snapshot = get_market_snapshot(config)
    
    # Extract decision parameters from config, using CLI overrides if provided
    basis_haircut = args.basis if args.basis else float(config["BASIS_ADJUSTMENT"])
    ops_buffer = args.ops_buffer if args.ops_buffer else float(config["OPS_BUFFER_USD"])
    decision_buffer = args.decision_buffer if args.decision_buffer else float(config["DECISION_BUFFER_USD"])
    coverage = args.coverage if args.coverage else float(config["COVERAGE_PCT"])
    ttf_lot = float(config["TTF_LOT_MMBTU"])
    jkm_lot = float(config["JKM_LOT_MMBTU"])
    
    # Run the trade decision engine
    trade_pack = run_trade_decision(
        routes=routes,
        vessels=vessels,
        carbon_params=carbon_params,
        load_port=args.load_port,
        europe_port=args.europe_port,
        asia_port=args.asia_port,
        vessel_class=args.vessel_class,
        cargo_capacity_m3=args.cargo_m3,
        ttf_price=market_snapshot.ttf_usd_mmbtu,
        jkm_price=market_snapshot.jkm_usd_mmbtu,
        freight_rate_usd_day=market_snapshot.freight_usd_day,
        fuel_price_usd_t=market_snapshot.fuel_usd_per_t,
        eua_price_usd_t=market_snapshot.eua_usd_per_tco2,
        basis_haircut_pct=basis_haircut,
        ops_buffer_usd=ops_buffer,
        decision_buffer_usd=decision_buffer,
        coverage_pct=coverage,
        ttf_lot_mmbtu=ttf_lot,
        jkm_lot_mmbtu=jkm_lot,
    )
    
    # Extract results for display
    decision = trade_pack["decision"]
    europe_result = trade_pack["europe"]
    asia_result = trade_pack["asia"]
    hedge_legs = trade_pack["hedge_legs"]
    
    # Print formatted trade note
    print("\n" + "="*60)
    print("LNG DIVERSION TRADE NOTE")
    print("="*60)
    print(f"Route: {args.load_port} → {args.europe_port} (TTF) vs {args.asia_port} (JKM)")
    print(f"Vessel: {args.vessel_class} | Cargo: {args.cargo_m3:,.0f} m³")
    print(f"As of: {market_snapshot.asof}")
    print("-"*60)
    
    # Market prices
    print(f"TTF: ${market_snapshot.ttf_usd_mmbtu:.2f}/MMBtu")
    print(f"JKM: ${market_snapshot.jkm_usd_mmbtu:.2f}/MMBtu (proxy)")
    print(f"Freight: ${market_snapshot.freight_usd_day:,.0f}/day (proxy)")
    print(f"Fuel: ${market_snapshot.fuel_usd_per_t:.0f}/t (proxy)")
    print(f"EUA: ${market_snapshot.eua_usd_per_tco2:.2f}/tCO₂ (proxy)")
    print("-"*60)
    
    # Netback comparison
    print(f"Europe netback: ${europe_result['netback_usd']:,.0f}")
    print(f"Asia netback:   ${asia_result['netback_usd']:,.0f}")
    print(f"Raw uplift:     ${decision['delta_raw_usd']:,.0f}")
    print(f"Adjusted uplift: ${decision['delta_adj_usd']:,.0f}")
    print(f"  (basis={basis_haircut:.1%}, ops=${ops_buffer:,.0f}, threshold=${decision_buffer:,.0f})")
    print("-"*60)
    
    # Final decision
    print(f"\n✓ Decision: {decision['decision']}")
    print("-"*60)
    
    # Hedge recommendation
    print(f"Hedge: {hedge_legs[0]['leg']} {hedge_legs[0]['lots']} lots | "
          f"{hedge_legs[1]['leg']} {hedge_legs[1]['lots']} lots")
    print("="*60 + "\n")
    
    # Save to file if requested
    if args.save:
        Path("reports").mkdir(exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        output_file = Path("reports") / f"trade_pack_{timestamp}.json"
        output_file.write_text(json.dumps(trade_pack, indent=2, default=str))
        print(f"✓ Saved: {output_file}\n")


if __name__ == "__main__":
    main()