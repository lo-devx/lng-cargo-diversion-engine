#!/usr/bin/env python3
"""
LNG Cargo Diversion Decision Engine

Main application entry point.

Usage:
    python app.py                    # Run for today's date
    python app.py --date 2026-01-28  # Run for specific date
    python app.py --backtest         # Run backtest on all available data
"""

import argparse
from datetime import datetime
import pandas as pd
import sys

from engine import (
    DataLoader,
    NetbackCalculator,
    DecisionEngine,
    RiskAnalyzer,
    Backtester,
    ReportGenerator
)


# Default voyage parameters
DEFAULT_LOAD_PORT = "US_Gulf"
DEFAULT_EUROPE_PORT = "Rotterdam"
DEFAULT_ASIA_PORT = "Tokyo"
DEFAULT_VESSEL_CLASS = "TFDE"


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="LNG Cargo Diversion Decision Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python app.py                        # Run for latest date in data
    python app.py --date 2026-01-28      # Run for specific date
    python app.py --backtest             # Run backtest on all data
    python app.py --load-port Qatar      # Use Qatar as load port
        """
    )
    
    parser.add_argument(
        "--date",
        type=str,
        help="Evaluation date (YYYY-MM-DD). Defaults to latest date in data."
    )
    
    parser.add_argument(
        "--backtest",
        action="store_true",
        help="Run backtest on all available historical data."
    )
    
    parser.add_argument(
        "--load-port",
        type=str,
        default=DEFAULT_LOAD_PORT,
        help=f"Load port (default: {DEFAULT_LOAD_PORT})"
    )
    
    parser.add_argument(
        "--europe-port",
        type=str,
        default=DEFAULT_EUROPE_PORT,
        help=f"Europe discharge port (default: {DEFAULT_EUROPE_PORT})"
    )
    
    parser.add_argument(
        "--asia-port",
        type=str,
        default=DEFAULT_ASIA_PORT,
        help=f"Asia discharge port (default: {DEFAULT_ASIA_PORT})"
    )
    
    parser.add_argument(
        "--vessel-class",
        type=str,
        default=DEFAULT_VESSEL_CLASS,
        choices=["TFDE", "MEGI"],
        help=f"Vessel class (default: {DEFAULT_VESSEL_CLASS})"
    )
    
    parser.add_argument(
        "--no-risk",
        action="store_true",
        help="Skip risk/stress analysis."
    )
    
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save reports to files."
    )
    
    return parser.parse_args()


def get_market_data_for_date(market_data, eval_date: datetime) -> dict:
    """Extract market data for a specific date."""
    date_pd = pd.Timestamp(eval_date)
    
    # Benchmark prices
    prices = market_data.benchmark_prices[
        market_data.benchmark_prices["date"] == date_pd
    ]
    if prices.empty:
        raise ValueError(f"No benchmark prices for date: {eval_date}")
    
    # Freight rates
    freight = market_data.freight_rates[
        market_data.freight_rates["date"] == date_pd
    ]
    if freight.empty:
        raise ValueError(f"No freight rates for date: {eval_date}")
    
    # Fuel prices
    fuel = market_data.fuel_prices[
        market_data.fuel_prices["date"] == date_pd
    ]
    if fuel.empty:
        raise ValueError(f"No fuel prices for date: {eval_date}")
    
    return {
        "ttf_price": prices["TTF"].values[0],
        "jkm_price": prices["JKM"].values[0],
        "tfde_freight": freight["TFDE_USD_day"].values[0],
        "megi_freight": freight["MEGI_USD_day"].values[0],
        "vlsfo_price": fuel["VLSFO_USD_per_t"].values[0],
        "lng_fuel_price": fuel["LNG_USD_per_t"].values[0]
    }


def run_single_evaluation(
    args,
    eval_date: datetime,
    market_data,
    static_data,
    config,
    netback_calc,
    decision_engine,
    risk_analyzer,
    report_gen
):
    """Run evaluation for a single date."""
    # Get market data for this date
    try:
        md = get_market_data_for_date(market_data, eval_date)
    except ValueError as e:
        print(f"Error: {e}")
        return None
    
    # Get vessel parameters
    vessel = static_data.vessels[
        static_data.vessels["vessel_class"] == args.vessel_class
    ].iloc[0]
    cargo_capacity_m3 = vessel["cargo_capacity_m3"]
    
    # Get freight rate for vessel class
    freight_rate = md["tfde_freight"] if args.vessel_class == "TFDE" else md["megi_freight"]
    
    # Get EUA price
    eua_price = static_data.carbon_params["EUA_price_USD_per_t"]
    
    # Calculate netbacks
    europe_netback, asia_netback = netback_calc.compare_netbacks(
        load_port=args.load_port,
        europe_port=args.europe_port,
        asia_port=args.asia_port,
        vessel_class=args.vessel_class,
        cargo_capacity_m3=cargo_capacity_m3,
        ttf_price=md["ttf_price"],
        jkm_price=md["jkm_price"],
        freight_rate_usd_day=freight_rate,
        fuel_price_usd_t=md["vlsfo_price"],
        eua_price_usd_t=eua_price
    )
    
    # Make decision
    result = decision_engine.evaluate(
        date=eval_date,
        europe_netback=europe_netback,
        asia_netback=asia_netback
    )
    
    # Run risk analysis
    risk_pack = None
    if not args.no_risk:
        risk_pack = risk_analyzer.run_stress_test(
            base_result=result,
            load_port=args.load_port,
            europe_port=args.europe_port,
            asia_port=args.asia_port,
            vessel_class=args.vessel_class,
            cargo_capacity_m3=cargo_capacity_m3,
            ttf_price=md["ttf_price"],
            jkm_price=md["jkm_price"],
            freight_rate_usd_day=freight_rate,
            fuel_price_usd_t=md["vlsfo_price"],
            eua_price_usd_t=eua_price
        )
    
    # Generate reports
    save = not args.no_save
    report_gen.generate_trade_ticket(result, save=save)
    
    if risk_pack:
        report_gen.generate_risk_report(risk_pack, save=save)
    
    # Print summary
    report_gen.print_summary(result, risk_pack)
    
    return result


def run_backtest(
    args,
    market_data,
    static_data,
    config,
    netback_calc,
    decision_engine,
    risk_analyzer,
    report_gen
):
    """Run backtest on all available data."""
    print("\nRunning backtest on all available data...")
    
    # Get all available dates
    dates = sorted(market_data.benchmark_prices["date"].unique())
    print(f"Found {len(dates)} dates in data.")
    
    results = []
    
    # Get vessel parameters
    vessel = static_data.vessels[
        static_data.vessels["vessel_class"] == args.vessel_class
    ].iloc[0]
    cargo_capacity_m3 = vessel["cargo_capacity_m3"]
    
    # Get EUA price
    eua_price = static_data.carbon_params["EUA_price_USD_per_t"]
    
    for date in dates:
        eval_date = date.to_pydatetime() if hasattr(date, 'to_pydatetime') else date
        
        try:
            md = get_market_data_for_date(market_data, eval_date)
        except ValueError:
            continue
        
        freight_rate = md["tfde_freight"] if args.vessel_class == "TFDE" else md["megi_freight"]
        
        # Calculate netbacks
        europe_netback, asia_netback = netback_calc.compare_netbacks(
            load_port=args.load_port,
            europe_port=args.europe_port,
            asia_port=args.asia_port,
            vessel_class=args.vessel_class,
            cargo_capacity_m3=cargo_capacity_m3,
            ttf_price=md["ttf_price"],
            jkm_price=md["jkm_price"],
            freight_rate_usd_day=freight_rate,
            fuel_price_usd_t=md["vlsfo_price"],
            eua_price_usd_t=eua_price
        )
        
        # Make decision
        result = decision_engine.evaluate(
            date=eval_date,
            europe_netback=europe_netback,
            asia_netback=asia_netback
        )
        
        results.append(result)
    
    # Run backtest analysis
    backtester = Backtester()
    backtest_result = backtester.run_backtest(results)
    
    # Generate report
    save = not args.no_save
    report_gen.generate_backtest_report(backtest_result, save=save)
    
    # Print backtest summary
    print("\n" + "=" * 60)
    print("BACKTEST RESULTS")
    print("=" * 60)
    metrics = backtest_result.metrics
    print(f"  Total Observations:       {metrics.total_observations}")
    print(f"  Triggered Trades:         {metrics.triggered_trades}")
    print(f"  Hit Rate:                 {metrics.hit_rate * 100:.1f}%")
    print(f"  Average Uplift (USD):     ${metrics.average_uplift_usd:,.2f}")
    print(f"  Total Uplift (USD):       ${metrics.total_uplift_usd:,.2f}")
    print(f"  Max Drawdown (USD):       ${metrics.max_drawdown_usd:,.2f}")
    if metrics.sharpe_ratio:
        print(f"  Sharpe Ratio (ann.):      {metrics.sharpe_ratio:.3f}")
    print("=" * 60)
    
    return backtest_result


def main():
    """Main entry point."""
    args = parse_args()
    
    print("\n" + "=" * 60)
    print("LNG CARGO DIVERSION DECISION ENGINE")
    print("=" * 60)
    
    # Load all data
    print("\nLoading data...")
    loader = DataLoader()
    try:
        market_data, static_data, config = loader.load_all()
        print("✅ Data loaded and validated successfully.")
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        sys.exit(1)
    
    # Print route info
    print(f"\nRoute: {args.load_port} → Europe ({args.europe_port}) / Asia ({args.asia_port})")
    print(f"Vessel Class: {args.vessel_class}")
    
    # Initialize components
    netback_calc = NetbackCalculator(
        routes=static_data.routes,
        vessels=static_data.vessels,
        carbon_params=static_data.carbon_params
    )
    
    decision_engine = DecisionEngine(
        decision_buffer_usd=config.decision_buffer_usd,
        operational_risk_buffer_usd=config.operational_risk_buffer_usd,
        basis_adjustment_pct=config.basis_adjustment_pct,
        coverage_pct=config.coverage_pct,
        jkm_lot_mmbtu=config.jkm_lot_mmbtu,
        ttf_lot_mmbtu=config.ttf_lot_mmbtu
    )
    
    risk_analyzer = RiskAnalyzer(
        netback_calculator=netback_calc,
        decision_engine=decision_engine,
        stress_spread_usd=config.stress_spread_usd,
        stress_freight_usd_per_day=config.stress_freight_usd_per_day,
        stress_eua_usd=config.stress_eua_usd
    )
    
    report_gen = ReportGenerator()
    
    # Run backtest or single evaluation
    if args.backtest:
        run_backtest(
            args,
            market_data,
            static_data,
            config,
            netback_calc,
            decision_engine,
            risk_analyzer,
            report_gen
        )
    else:
        # Determine evaluation date
        if args.date:
            eval_date = datetime.strptime(args.date, "%Y-%m-%d")
        else:
            # Use latest date in data
            eval_date = market_data.benchmark_prices["date"].max()
            if hasattr(eval_date, 'to_pydatetime'):
                eval_date = eval_date.to_pydatetime()
        
        run_single_evaluation(
            args,
            eval_date,
            market_data,
            static_data,
            config,
            netback_calc,
            decision_engine,
            risk_analyzer,
            report_gen
        )
    
    print("\n✅ Done.")


if __name__ == "__main__":
    main()
