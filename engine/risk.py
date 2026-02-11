"""
LNG Cargo Diversion Decision Engine

Risk and stress testing module.
"""

from dataclasses import dataclass
from typing import List, Dict
import pandas as pd

from .netback import NetbackCalculator, NetbackResult
from .decision import decide_and_size, DecisionResult


@dataclass
class StressScenario:
    """A single stress scenario."""
    name: str
    spread_shock_usd: float = 0.0  # Change in JKM-TTF spread
    freight_shock_usd_day: float = 0.0  # Change in freight rate
    eua_shock_usd: float = 0.0  # Change in EUA price


@dataclass
class StressResult:
    """Result of a stress test."""
    scenario: StressScenario
    base_delta_netback_adj: float
    stressed_delta_netback_adj: float
    pnl_impact_usd: float
    decision_change: bool  # Did the decision flip?
    base_decision: str
    stressed_decision: str


@dataclass
class RiskPack:
    """Complete risk pack with all stress results."""
    base_result: DecisionResult
    stress_results: List[StressResult]
    worst_case_pnl_impact: float
    scenarios_causing_flip: List[str]


class RiskAnalyzer:
    """Analyze risk through stress testing."""
    
    def __init__(
        self,
        netback_calculator: NetbackCalculator,
        stress_spread_usd: float,
        stress_freight_usd_per_day: float,
        stress_eua_usd: float,
        basis_haircut_pct: float = 0.05,
        ops_buffer_usd: float = 50000,
        decision_buffer_usd: float = 500000
    ):
        self.netback_calculator = netback_calculator
        self.stress_spread_usd = stress_spread_usd
        self.stress_freight_usd_per_day = stress_freight_usd_per_day
        self.stress_eua_usd = stress_eua_usd
        self.basis_haircut_pct = basis_haircut_pct
        self.ops_buffer_usd = ops_buffer_usd
        self.decision_buffer_usd = decision_buffer_usd
    
    def create_scenarios(self) -> List[StressScenario]:
        """Create standard stress scenarios."""
        return [
            StressScenario(
                name="Spread Collapse",
                spread_shock_usd=-self.stress_spread_usd
            ),
            StressScenario(
                name="Spread Widen",
                spread_shock_usd=self.stress_spread_usd
            ),
            StressScenario(
                name="Freight Spike",
                freight_shock_usd_day=self.stress_freight_usd_per_day
            ),
            StressScenario(
                name="Freight Drop",
                freight_shock_usd_day=-self.stress_freight_usd_per_day
            ),
            StressScenario(
                name="EUA Spike",
                eua_shock_usd=self.stress_eua_usd
            ),
            StressScenario(
                name="Combined Adverse",
                spread_shock_usd=-self.stress_spread_usd,
                freight_shock_usd_day=self.stress_freight_usd_per_day,
                eua_shock_usd=self.stress_eua_usd
            )
        ]
    
    def run_stress_test(
        self,
        base_result: DecisionResult,
        load_port: str,
        europe_port: str,
        asia_port: str,
        vessel_class: str,
        cargo_capacity_m3: float,
        ttf_price: float,
        jkm_price: float,
        freight_rate_usd_day: float,
        fuel_price_usd_t: float,
        eua_price_usd_t: float
    ) -> RiskPack:
        """Run all stress scenarios and produce risk pack."""
        scenarios = self.create_scenarios()
        stress_results = []
        
        for scenario in scenarios:
            # Apply shocks
            stressed_jkm = jkm_price + scenario.spread_shock_usd
            stressed_freight = freight_rate_usd_day + scenario.freight_shock_usd_day
            stressed_eua = eua_price_usd_t + scenario.eua_shock_usd
            
            # Recalculate netbacks with stressed values
            europe_netback, asia_netback = self.netback_calculator.compare_netbacks(
                load_port=load_port,
                europe_port=europe_port,
                asia_port=asia_port,
                vessel_class=vessel_class,
                cargo_capacity_m3=cargo_capacity_m3,
                ttf_price=ttf_price,
                jkm_price=stressed_jkm,
                freight_rate_usd_day=stressed_freight,
                fuel_price_usd_t=fuel_price_usd_t,
                eua_price_usd_t=stressed_eua
            )
            
            # Re-evaluate decision
            stressed_result = decide_and_size(
                europe_netback_usd=europe_netback.netback_usd,
                asia_netback_usd=asia_netback.netback_usd,
                hedge_energy_mmbtu=asia_netback.delivered_energy_mmbtu,
                basis_haircut_pct=self.basis_haircut_pct,
                ops_buffer_usd=self.ops_buffer_usd,
                decision_buffer_usd=self.decision_buffer_usd
            )
            
            # Calculate P&L impact
            pnl_impact = stressed_result.delta_netback_adj_usd - base_result.delta_netback_adj_usd
            
            stress_results.append(StressResult(
                scenario=scenario,
                base_delta_netback_adj=base_result.delta_netback_adj_usd,
                stressed_delta_netback_adj=stressed_result.delta_netback_adj_usd,
                pnl_impact_usd=pnl_impact,
                decision_change=stressed_result.decision != base_result.decision,
                base_decision=base_result.decision,
                stressed_decision=stressed_result.decision
            ))
        
        # Find worst case and scenarios causing flip
        worst_case_pnl = min(r.pnl_impact_usd for r in stress_results)
        scenarios_causing_flip = [
            r.scenario.name for r in stress_results if r.decision_change
        ]
        
        return RiskPack(
            base_result=base_result,
            stress_results=stress_results,
            worst_case_pnl_impact=worst_case_pnl,
            scenarios_causing_flip=scenarios_causing_flip
        )
