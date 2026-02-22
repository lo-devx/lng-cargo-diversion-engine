"""
LNG Cargo Diversion Decision Engine 

Objective:
Determines whether to divert an LNG cargo from Europe (TTF) to Asia (JKM)
based on netback analysis, accounting for voyage costs, freight rates, and
carbon pricing. Outputs a trade decision (DIVERT/KEEP) and hedge recommendations.

Run with: 
    python app.py                    # Basic run with defaults
    python app.py --save             # Save JSON + CSV reports
    python app.py --basis 0.03       # Override basis adjustment
    python app.py --help             # See all options

Saved Reports (with --save flag):
    reports/trade_pack_YYYYMMDD_HHMMSS.json    - Complete decision data (for systems/APIs)
    reports/trade_ticket_YYYYMMDD_HHMMSS.csv   - Flat key-value format (for desk review)
"""

import argparse
from pathlib import Path
import json
from datetime import datetime

from engine.data_loader import load_routes, load_vessels, load_carbon_params, load_config, load_benchmark_prices, load_aux_series
from engine.market_data import get_market_snapshot
from engine.run import run_trade_decision
from engine.reports import save_trade_pack, save_trade_ticket_csv
from engine.backtest import Backtester
from types import SimpleNamespace


def run_backtest(args):
    """Run backtest mode with historical data."""
    print("\n" + "="*60)
    print("BACKTEST MODE")
    print("="*60)
    
    # Load static data
    routes = load_routes()
    vessels = load_vessels()
    carbon_params = load_carbon_params()
    config = load_config()
    
    # Load historical data
    print("Loading historical data...")
    benchmark_prices = load_benchmark_prices()
    aux_series = load_aux_series()
    
    # Merge on date
    historical_data = benchmark_prices.merge(aux_series, on="date")
    print(f"Loaded {len(historical_data)} days of data")
    print(f"Date range: {historical_data['date'].min().date()} to {historical_data['date'].max().date()}")
    
    # Extract decision parameters from config
    basis_haircut = args.basis if args.basis else float(config["BASIS_ADJUSTMENT"])
    ops_buffer = args.ops_buffer if args.ops_buffer else float(config["OPS_BUFFER_USD"])
    decision_buffer = args.decision_buffer if args.decision_buffer else float(config["DECISION_BUFFER_USD"])
    coverage = args.coverage if args.coverage else float(config["COVERAGE_PCT"])
    ttf_lot = float(config["TTF_LOT_MMBTU"])
    jkm_lot = float(config["JKM_LOT_MMBTU"])
    
    # Run decision engine for each day
    print("\nRunning decision engine for each day...")
    results = []
    
    for _, row in historical_data.iterrows():
        trade_pack = run_trade_decision(
            routes=routes,
            vessels=vessels,
            carbon_params=carbon_params,
            load_port=args.load_port,
            europe_port=args.europe_port,
            asia_port=args.asia_port,
            vessel_class=args.vessel_class,
            cargo_capacity_m3=args.cargo_m3,
            ttf_price=row["TTF_USD_MMBTU"],
            jkm_price=row["JKM_USD_MMBTU"],
            freight_rate_usd_day=row["FREIGHT_USD_DAY"],
            fuel_price_usd_t=row["FUEL_USD_PER_T"],
            eua_price_usd_t=row["EUA_USD_PER_TCO2"],
            basis_haircut_pct=basis_haircut,
            ops_buffer_usd=ops_buffer,
            decision_buffer_usd=decision_buffer,
            coverage_pct=coverage,
            ttf_lot_mmbtu=ttf_lot,
            jkm_lot_mmbtu=jkm_lot,
        )
        
        # Create simple result dict with date
        # Create netback objects expected by backtester
        europe_nb = SimpleNamespace(netback_usd=trade_pack["europe"]["netback_usd"])
        asia_nb = SimpleNamespace(netback_usd=trade_pack["asia"]["netback_usd"])
        
        result = SimpleNamespace(
            date=row["date"].date(),
            decision=trade_pack["decision"]["decision"],
            delta_netback_raw_usd=trade_pack["decision"]["delta_raw_usd"],
            delta_netback_adj_usd=trade_pack["decision"]["delta_adj_usd"],
            europe_netback=europe_nb,
            asia_netback=asia_nb,
        )
        results.append(result)
    
    # Run backtest analysis
    print("Analyzing backtest results...")
    backtester = Backtester()
    backtest_result = backtester.run_backtest(results)
    
    # Display metrics
    metrics = backtest_result.metrics
    print("\n" + "="*60)
    print("RULE VALIDATION (Backtest)")
    print("="*60)
    print("⚠️  Note: Measures trigger frequency & conditional uplift,")
    print("    not actual trading P&L (no slippage, basis risk, hedging costs)")
    print("="*60)
    print(f"Observation period: {metrics.total_observations} days")
    print(f"Average conditional uplift: ${metrics.average_uplift_usd:,.0f}")
    print(f"Total conditional uplift: ${metrics.total_uplift_usd:,.0f}")
    print("="*60)
    
    # Save results if requested
    if args.save:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        # Save equity curve
        equity_path = Path(f"reports/equity_curve_{timestamp}.csv")
        backtest_result.equity_curve.to_csv(equity_path, index=False)
        print(f"\nSaved: {equity_path}")
        
        # Save decision history
        trades_path = Path(f"reports/backtest_trades_{timestamp}.csv")
        backtest_result.decision_history.to_csv(trades_path, index=False)
        print(f"Saved: {trades_path}")


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
    parser.add_argument("--backtest", action="store_true", help="Run backtest mode with historical data")
    
    args = parser.parse_args()
    
    # Run backtest if requested
    if args.backtest:
        run_backtest(args)
        return
    
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
    
    # Market prices with provenance
    prov = market_snapshot.provenance
    print(f"TTF: ${market_snapshot.ttf_usd_mmbtu:.2f}/MMBtu ({prov['TTF']})")
    print(f"JKM: ${market_snapshot.jkm_usd_mmbtu:.2f}/MMBtu ({prov['JKM']})")
    print(f"Freight: ${market_snapshot.freight_usd_day:,.0f}/day ({prov['FREIGHT']})")
    print(f"Fuel: ${market_snapshot.fuel_usd_per_t:.0f}/t ({prov['FUEL']})")
    print(f"EUA: ${market_snapshot.eua_usd_per_tco2:.2f}/tCO₂ ({prov['EUA']})")
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
        p1 = save_trade_pack(trade_pack)
        p2 = save_trade_ticket_csv(trade_pack)
        print(f"Saved: {p1}")
        print(f"Saved: {p2}")


if __name__ == "__main__":
    main()