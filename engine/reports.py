"""
LNG Cargo Diversion Decision Engine

Report generation module.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional
import pandas as pd

from .decision import DecisionResult
from .risk import RiskPack
from .backtest import BacktestResult


class ReportGenerator:
    """Generate and save reports."""
    
    def __init__(self, output_dir: str = "reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def generate_trade_ticket(
        self,
        result: DecisionResult,
        save: bool = True
    ) -> dict:
        """Generate trade ticket as dict and optionally save to file."""
        ticket = {
            "timestamp": result.date.isoformat() if isinstance(result.date, datetime) else str(result.date),
            "decision": result.decision,
            "netback_europe_usd": round(result.europe_netback.netback_usd, 2),
            "netback_asia_usd": round(result.asia_netback.netback_usd, 2),
            "delta_netback_raw_usd": round(result.delta_netback_raw_usd, 2),
            "delta_netback_adj_usd": round(result.delta_netback_adj_usd, 2),
            "decision_buffer_usd": round(result.decision_buffer_usd, 2),
            "basis_adjustment_pct": result.basis_adjustment_pct,
            "operational_risk_buffer_usd": round(result.operational_risk_buffer_usd, 2),
        }
        
        if result.decision == "DIVERT":
            ticket["hedge"] = {
                "legs": result.trade_ticket.hedge_legs,
                "jkm_lots": result.trade_ticket.jkm_lots,
                "ttf_lots": result.trade_ticket.ttf_lots,
                "hedge_energy_mmbtu": round(result.trade_ticket.hedge_energy_mmbtu, 2)
            }
        
        if save:
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            date_str = result.date.strftime("%Y%m%d") if isinstance(result.date, datetime) else str(result.date).replace("-", "")
            filename = f"trade_ticket_{date_str}_{timestamp_str}.json"
            
            with open(self.output_dir / filename, "w") as f:
                json.dump(ticket, f, indent=2)
            
            print(f"Trade ticket saved to: {self.output_dir / filename}")
        
        return ticket
    
    def generate_risk_report(
        self,
        risk_pack: RiskPack,
        save: bool = True
    ) -> dict:
        """Generate risk report as dict and optionally save to file."""
        report = {
            "evaluation_date": str(risk_pack.base_result.date),
            "base_decision": risk_pack.base_result.decision,
            "base_delta_netback_adj_usd": round(risk_pack.base_result.delta_netback_adj_usd, 2),
            "worst_case_pnl_impact_usd": round(risk_pack.worst_case_pnl_impact, 2),
            "scenarios_causing_decision_flip": risk_pack.scenarios_causing_flip,
            "stress_scenarios": []
        }
        
        for sr in risk_pack.stress_results:
            report["stress_scenarios"].append({
                "scenario_name": sr.scenario.name,
                "spread_shock_usd": sr.scenario.spread_shock_usd,
                "freight_shock_usd_day": sr.scenario.freight_shock_usd_day,
                "eua_shock_usd": sr.scenario.eua_shock_usd,
                "pnl_impact_usd": round(sr.pnl_impact_usd, 2),
                "stressed_delta_netback_adj_usd": round(sr.stressed_delta_netback_adj, 2),
                "decision_flipped": sr.decision_change,
                "stressed_decision": sr.stressed_decision
            })
        
        if save:
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"risk_report_{timestamp_str}.json"
            
            with open(self.output_dir / filename, "w") as f:
                json.dump(report, f, indent=2)
            
            print(f"Risk report saved to: {self.output_dir / filename}")
        
        return report
    
    def generate_backtest_report(
        self,
        backtest_result: BacktestResult,
        save: bool = True
    ) -> dict:
        """Generate backtest report as dict and optionally save to file."""
        metrics = backtest_result.metrics
        
        report = {
            "backtest_summary": {
                "total_observations": metrics.total_observations,
                "triggered_trades": metrics.triggered_trades,
                "hit_rate_pct": round(metrics.hit_rate * 100, 2),
                "average_uplift_usd": round(metrics.average_uplift_usd, 2),
                "total_uplift_usd": round(metrics.total_uplift_usd, 2),
                "max_drawdown_usd": round(metrics.max_drawdown_usd, 2),
                "sharpe_ratio": round(metrics.sharpe_ratio, 3) if metrics.sharpe_ratio else None
            },
            "equity_curve": backtest_result.equity_curve.to_dict(orient="records")
        }
        
        if save:
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"backtest_report_{timestamp_str}.json"
            
            with open(self.output_dir / filename, "w") as f:
                json.dump(report, f, indent=2, default=str)
            
            print(f"Backtest report saved to: {self.output_dir / filename}")
            
            # Also save equity curve as CSV
            equity_filename = f"equity_curve_{timestamp_str}.csv"
            backtest_result.equity_curve.to_csv(
                self.output_dir / equity_filename,
                index=False
            )
            print(f"Equity curve saved to: {self.output_dir / equity_filename}")
        
        return report
    
    def print_summary(self, result: DecisionResult, risk_pack: Optional[RiskPack] = None):
        """Print a formatted summary to console."""
        print("\n" + "=" * 60)
        print("LNG CARGO DIVERSION DECISION ENGINE - SUMMARY")
        print("=" * 60)
        
        print(f"\nEvaluation Date: {result.date}")
        print(f"\n{'NETBACK COMPARISON':-^60}")
        print(f"  Europe (TTF) Netback:     ${result.europe_netback.netback_usd:>15,.2f}")
        print(f"  Asia (JKM) Netback:       ${result.asia_netback.netback_usd:>15,.2f}")
        print(f"  ΔNetback (raw):           ${result.delta_netback_raw_usd:>15,.2f}")
        print(f"  ΔNetback (adjusted):      ${result.delta_netback_adj_usd:>15,.2f}")
        print(f"  Decision Buffer:          ${result.decision_buffer_usd:>15,.2f}")
        
        print(f"\n{'DECISION':-^60}")
        decision_color = "✅" if result.decision == "DIVERT" else "🔄"
        print(f"  {decision_color} Decision: {result.decision}")
        
        if result.decision == "DIVERT":
            print(f"\n{'TRADE TICKET':-^60}")
            print(f"  Hedge Legs:")
            for leg in result.trade_ticket.hedge_legs:
                print(f"    - {leg['leg']} {leg['instrument']}: {leg['lots']} lots")
            print(f"  Hedge Energy: {result.trade_ticket.hedge_energy_mmbtu:,.0f} MMBtu")
        
        if risk_pack:
            print(f"\n{'RISK PACK':-^60}")
            print(f"  Worst Case P&L Impact:    ${risk_pack.worst_case_pnl_impact:>15,.2f}")
            if risk_pack.scenarios_causing_flip:
                print(f"  ⚠️  Scenarios causing decision flip:")
                for scenario in risk_pack.scenarios_causing_flip:
                    print(f"      - {scenario}")
            else:
                print(f"  ✅ No scenarios cause decision flip")
        
        print("\n" + "=" * 60)
