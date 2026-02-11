"""
LNG Cargo Diversion Decision Engine

Decision engine module - applies rules and generates trade decisions.
"""

# engine/decision.py

from dataclasses import dataclass

import math

from typing import Dict, Any

@dataclass

class DecisionResult:

    delta_netback_raw_usd: float

    delta_netback_adj_usd: float

    basis_haircut_pct: float     # 0-1

    ops_buffer_usd: float

    decision_buffer_usd: float

    decision: str                # "DIVERT" or "KEEP"

    hedge_energy_mmbtu: float

    lots_ttf: int

    lots_jkm: int

def decide_and_size(

    europe_netback_usd: float,

    asia_netback_usd: float,

    hedge_energy_mmbtu: float,

    *,

    basis_haircut_pct: float,

    ops_buffer_usd: float,

    decision_buffer_usd: float,

    ttf_lot_mmbtu: float = 10000,

    jkm_lot_mmbtu: float = 10000,

) -> DecisionResult:

    """

    Apply the rule:

      Δraw = Asia - Europe

      Δadj = Δraw * (1 - haircut) - ops_buffer

      DIVERT if Δadj >= decision_buffer else KEEP

    """

    delta_raw = asia_netback_usd - europe_netback_usd

    delta_adj = delta_raw * (1.0 - basis_haircut_pct) - ops_buffer_usd

    decision = "DIVERT" if delta_adj >= decision_buffer_usd else "KEEP"

    lots_ttf = math.floor(hedge_energy_mmbtu / ttf_lot_mmbtu)

    lots_jkm = math.floor(hedge_energy_mmbtu / jkm_lot_mmbtu)

    return DecisionResult(

        delta_netback_raw_usd=delta_raw,

        delta_netback_adj_usd=delta_adj,

        basis_haircut_pct=basis_haircut_pct,

        ops_buffer_usd=ops_buffer_usd,

        decision_buffer_usd=decision_buffer_usd,

        decision=decision,

        hedge_energy_mmbtu=hedge_energy_mmbtu,

        lots_ttf=lots_ttf,

        lots_jkm=lots_jkm,

    )
 