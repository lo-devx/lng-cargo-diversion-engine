"""
LNG Cargo Diversion Decision Engine

Decision engine module - applies rules and generates trade decisions.
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime
import math

from .netback import NetbackResult


@dataclass
class TradeTicket:
    """Trade ticket with hedge details."""
    timestamp: datetime
    decision: str  # "DIVERT" or "KEEP"
    delta_netback_raw_usd: float
    delta_netback_adj_usd: float
    decision_buffer_usd: float
    
    # Hedge details (only if DIVERT)
    hedge_legs: Optional[list] = None
    jkm_lots: Optional[int] = None
    ttf_lots: Optional[int] = None
    hedge_energy_mmbtu: Optional[float] = None
    
    # Netback details
    netback_europe_usd: Optional[float] = None
    netback_asia_usd: Optional[float] = None


@dataclass
class DecisionResult:
    """Full decision result with all details."""
    date: datetime
    europe_netback: NetbackResult
    asia_netback: NetbackResult
    delta_netback_raw_usd: float
    delta_netback_adj_usd: float
    decision: str
    trade_ticket: TradeTicket
    
    # Config used
    basis_adjustment_pct: float
    operational_risk_buffer_usd: float
    decision_buffer_usd: float


class DecisionEngine:
    """
    Decision engine that applies the diversion rule.
    
    Rule: Divert to Asia when ΔNetback_adj ≥ DecisionBuffer
    Where:
        ΔNetback_raw = Netback_Asia − Netback_Europe
        ΔNetback_adj = ΔNetback_raw × (1 − BasisAdjustment) − OperationalRiskBuffer
    """
    
    def __init__(
        self,
        decision_buffer_usd: float,
        operational_risk_buffer_usd: float,
        basis_adjustment_pct: float,
        coverage_pct: float,
        jkm_lot_mmbtu: float,
        ttf_lot_mmbtu: float
    ):
        self.decision_buffer_usd = decision_buffer_usd
        self.operational_risk_buffer_usd = operational_risk_buffer_usd
        self.basis_adjustment_pct = basis_adjustment_pct
        self.coverage_pct = coverage_pct
        self.jkm_lot_mmbtu = jkm_lot_mmbtu
        self.ttf_lot_mmbtu = ttf_lot_mmbtu
    
    def evaluate(
        self,
        date: datetime,
        europe_netback: NetbackResult,
        asia_netback: NetbackResult
    ) -> DecisionResult:
        """
        Evaluate the diversion decision for a given date.
        
        Returns full decision result with trade ticket.
        """
        # Calculate delta netback
        delta_netback_raw = asia_netback.netback_usd - europe_netback.netback_usd
        
        # Apply conservative adjustments
        delta_netback_adj = (
            delta_netback_raw * (1 - self.basis_adjustment_pct) 
            - self.operational_risk_buffer_usd
        )
        
        # Apply decision rule
        if delta_netback_adj >= self.decision_buffer_usd:
            decision = "DIVERT"
            trade_ticket = self._create_divert_ticket(
                date=date,
                delta_netback_raw=delta_netback_raw,
                delta_netback_adj=delta_netback_adj,
                europe_netback=europe_netback,
                asia_netback=asia_netback
            )
        else:
            decision = "KEEP"
            trade_ticket = self._create_keep_ticket(
                date=date,
                delta_netback_raw=delta_netback_raw,
                delta_netback_adj=delta_netback_adj,
                europe_netback=europe_netback,
                asia_netback=asia_netback
            )
        
        return DecisionResult(
            date=date,
            europe_netback=europe_netback,
            asia_netback=asia_netback,
            delta_netback_raw_usd=delta_netback_raw,
            delta_netback_adj_usd=delta_netback_adj,
            decision=decision,
            trade_ticket=trade_ticket,
            basis_adjustment_pct=self.basis_adjustment_pct,
            operational_risk_buffer_usd=self.operational_risk_buffer_usd,
            decision_buffer_usd=self.decision_buffer_usd
        )
    
    def _create_divert_ticket(
        self,
        date: datetime,
        delta_netback_raw: float,
        delta_netback_adj: float,
        europe_netback: NetbackResult,
        asia_netback: NetbackResult
    ) -> TradeTicket:
        """Create trade ticket for DIVERT decision."""
        # Calculate hedge size based on coverage
        delivered_energy = asia_netback.delivered_energy_mmbtu
        hedge_energy = delivered_energy * self.coverage_pct
        
        # Calculate lots (round down to be conservative)
        jkm_lots = math.floor(hedge_energy / self.jkm_lot_mmbtu)
        ttf_lots = math.floor(hedge_energy / self.ttf_lot_mmbtu)
        
        return TradeTicket(
            timestamp=date,
            decision="DIVERT",
            delta_netback_raw_usd=delta_netback_raw,
            delta_netback_adj_usd=delta_netback_adj,
            decision_buffer_usd=self.decision_buffer_usd,
            hedge_legs=[
                {"leg": "LONG", "instrument": "JKM", "lots": jkm_lots},
                {"leg": "SHORT", "instrument": "TTF", "lots": ttf_lots}
            ],
            jkm_lots=jkm_lots,
            ttf_lots=ttf_lots,
            hedge_energy_mmbtu=hedge_energy,
            netback_europe_usd=europe_netback.netback_usd,
            netback_asia_usd=asia_netback.netback_usd
        )
    
    def _create_keep_ticket(
        self,
        date: datetime,
        delta_netback_raw: float,
        delta_netback_adj: float,
        europe_netback: NetbackResult,
        asia_netback: NetbackResult
    ) -> TradeTicket:
        """Create trade ticket for KEEP decision (no hedge)."""
        return TradeTicket(
            timestamp=date,
            decision="KEEP",
            delta_netback_raw_usd=delta_netback_raw,
            delta_netback_adj_usd=delta_netback_adj,
            decision_buffer_usd=self.decision_buffer_usd,
            hedge_legs=None,
            jkm_lots=None,
            ttf_lots=None,
            hedge_energy_mmbtu=None,
            netback_europe_usd=europe_netback.netback_usd,
            netback_asia_usd=asia_netback.netback_usd
        )
