from typing import Dict, Any

import pandas as pd

from engine.netback import NetbackCalculator

from engine.decision import decide_and_size

def run_trade_decision(

    *,

    routes: pd.DataFrame,

    vessels: pd.DataFrame,

    carbon_params: Dict[str, float],

    load_port: str,

    europe_port: str,

    asia_port: str,

    vessel_class: str,

    cargo_capacity_m3: float,

    ttf_price: float,

    jkm_price: float,

    freight_rate_usd_day: float,

    fuel_price_usd_t: float,

    eua_price_usd_t: float,

    # decision knobs

    basis_haircut_pct: float,

    ops_buffer_usd: float,

    decision_buffer_usd: float,

    coverage_pct: float = 0.80,

    ttf_lot_mmbtu: float = 10000,

    jkm_lot_mmbtu: float = 10000,

) -> Dict[str, Any]:

    """

    One-call engine:

    - compute Europe & Asia netbacks

    - compute delta + adjusted delta

    - compute decision + hedge sizing

    Returns a dict suitable for Dash + report export.

    """

    calc = NetbackCalculator(routes=routes, vessels=vessels, carbon_params=carbon_params)

    eu, asia = calc.compare_netbacks(

        load_port=load_port,

        europe_port=europe_port,

        asia_port=asia_port,

        vessel_class=vessel_class,

        cargo_capacity_m3=cargo_capacity_m3,

        ttf_price=ttf_price,

        jkm_price=jkm_price,

        freight_rate_usd_day=freight_rate_usd_day,

        fuel_price_usd_t=fuel_price_usd_t,

        eua_price_usd_t=eua_price_usd_t,

    )

    # Hedge energy: use max delivered energy * coverage (simple & conservative)

    hedge_energy_mmbtu = max(eu.delivered_energy_mmbtu, asia.delivered_energy_mmbtu) * coverage_pct

    decision = decide_and_size(

        europe_netback_usd=eu.netback_usd,

        asia_netback_usd=asia.netback_usd,

        hedge_energy_mmbtu=hedge_energy_mmbtu,

        basis_haircut_pct=basis_haircut_pct,

        ops_buffer_usd=ops_buffer_usd,

        decision_buffer_usd=decision_buffer_usd,

        ttf_lot_mmbtu=ttf_lot_mmbtu,

        jkm_lot_mmbtu=jkm_lot_mmbtu,

    )

    # Build trade pack

    return {

        "inputs": {

            "load_port": load_port,

            "europe_port": europe_port,

            "asia_port": asia_port,

            "vessel_class": vessel_class,

            "cargo_capacity_m3": cargo_capacity_m3,

            "ttf_price": ttf_price,

            "jkm_price": jkm_price,

            "freight_rate_usd_day": freight_rate_usd_day,

            "fuel_price_usd_t": fuel_price_usd_t,

            "eua_price_usd_t": eua_price_usd_t,

            "basis_haircut_pct": basis_haircut_pct,

            "ops_buffer_usd": ops_buffer_usd,

            "decision_buffer_usd": decision_buffer_usd,

            "coverage_pct": coverage_pct,

            "ttf_lot_mmbtu": ttf_lot_mmbtu,

            "jkm_lot_mmbtu": jkm_lot_mmbtu,

        },

        "europe": {

            "netback_usd": eu.netback_usd,

            "revenue_usd": eu.revenue_usd,

            "voyage_cost_usd": eu.voyage_cost_usd,

            "carbon_cost_usd": eu.carbon_cost_usd,

            "delivered_energy_mmbtu": eu.delivered_energy_mmbtu,

            "voyage_days": eu.voyage_details.voyage_days,

        },

        "asia": {

            "netback_usd": asia.netback_usd,

            "revenue_usd": asia.revenue_usd,

            "voyage_cost_usd": asia.voyage_cost_usd,

            "carbon_cost_usd": asia.carbon_cost_usd,

            "delivered_energy_mmbtu": asia.delivered_energy_mmbtu,

            "voyage_days": asia.voyage_details.voyage_days,

        },

        "decision": {

            "delta_raw_usd": decision.delta_netback_raw_usd,

            "delta_adj_usd": decision.delta_netback_adj_usd,

            "decision": decision.decision,

            "hedge_energy_mmbtu": decision.hedge_energy_mmbtu,

            "lots_ttf": decision.lots_ttf,

            "lots_jkm": decision.lots_jkm,

        },

        "hedge_legs": (

            [{"leg": "BUY JKM", "lots": decision.lots_jkm}, {"leg": "SELL TTF", "lots": decision.lots_ttf}]

            if decision.decision == "DIVERT"

            else [{"leg": "BUY TTF", "lots": decision.lots_ttf}, {"leg": "SELL JKM", "lots": decision.lots_jkm}]

        ),

    }
 