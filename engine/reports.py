"""
LNG Cargo Diversion Decision Engine - Report Generation

This module handles all output generation for trade decisions:
- save_trade_pack(): Saves complete decision data as JSON
- save_trade_ticket_csv(): Creates desk-friendly CSV with key trade parameters
- save_stress_csv(): Exports stress test scenarios and results

All reports are saved to reports/ with UTC timestamps. The trade ticket CSV
includes route details, live market data (TTF/EUA from Yahoo Finance), netback
calculations, and hedge recommendations for trading desk review.
"""

from __future__ import annotations
from dataclasses import asdict, is_dataclass
from pathlib import Path
from datetime import datetime
import csv
import json
from typing import Any, Dict, List

REPORTS_DIR = Path("reports")


def _timestamp() -> str:
    """Return UTC timestamp in YYYYmmdd_HHMMSS format."""
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")


def _to_json_serializable(obj: Any) -> Any:
    """
    Recursively convert dataclasses and nested structures to JSON-serializable types.
    Handles dataclasses, dicts, and lists.
    """
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, dict):
        return {k: _to_json_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_json_serializable(x) for x in obj]
    return obj


def save_trade_pack(pack: Dict[str, Any], *, prefix: str = "trade_pack") -> Path:
    """
    Save complete trade pack as JSON with all inputs, decisions, and hedge recommendations.
    
    Args:
        pack: Dictionary containing inputs, decision, europe, asia, and hedge_legs
        prefix: Filename prefix (default: "trade_pack")
    
    Returns:
        Path to saved JSON file
    """
    REPORTS_DIR.mkdir(exist_ok=True)
    filepath = REPORTS_DIR / f"{prefix}_{_timestamp()}.json"
    
    json_data = json.dumps(_to_json_serializable(pack), indent=2, default=str)
    filepath.write_text(json_data)
    
    return filepath


def save_trade_ticket_csv(pack: Dict[str, Any], *, prefix: str = "trade_ticket") -> Path:
    """
    Generate flat CSV trade ticket for desk review.
    Extracts key fields from trade pack into human-readable format.
    
    Args:
        pack: Trade pack from engine/run.py
        prefix: Filename prefix (default: "trade_ticket")
    
    Returns:
        Path to saved CSV file
    """
    REPORTS_DIR.mkdir(exist_ok=True)
    filepath = REPORTS_DIR / f"{prefix}_{_timestamp()}.csv"
    
    # Extract sections from pack
    inputs = pack["inputs"]
    decision = pack["decision"]
    europe = pack["europe"]
    asia = pack["asia"]
    hedge_legs = pack["hedge_legs"]
    
    # Build flat key-value rows
    rows = [
        ("timestamp_utc", datetime.utcnow().isoformat(timespec="seconds")),
        
        # Route and vessel
        ("load_port", inputs["load_port"]),
        ("europe_port", inputs["europe_port"]),
        ("asia_port", inputs["asia_port"]),
        ("vessel_class", inputs["vessel_class"]),
        ("cargo_capacity_m3", inputs["cargo_capacity_m3"]),
        
        # Market data (real from Yahoo Finance: TTF, EUA)
        ("TTF_USD_MMBtu", inputs["ttf_price"]),
        ("JKM_USD_MMBtu", inputs["jkm_price"]),
        ("freight_USD_day", inputs["freight_rate_usd_day"]),
        ("fuel_USD_t", inputs["fuel_price_usd_t"]),
        ("EUA_USD_tCO2", inputs["eua_price_usd_t"]),
        
        # Netback comparison
        ("europe_netback_USD", europe["netback_usd"]),
        ("asia_netback_USD", asia["netback_usd"]),
        ("delta_raw_USD", decision["delta_raw_usd"]),
        
        # Decision parameters
        ("basis_haircut", inputs["basis_haircut_pct"]),
        ("ops_buffer_USD", inputs["ops_buffer_usd"]),
        ("decision_buffer_USD", inputs["decision_buffer_usd"]),
        ("delta_adj_USD", decision["delta_adj_usd"]),
        
        # Final decision and hedging
        ("decision", decision["decision"]),
        ("hedge_energy_MMBtu", decision["hedge_energy_mmbtu"]),
        ("hedge_leg_1", f"{hedge_legs[0]['leg']} {hedge_legs[0]['lots']} lots"),
        ("hedge_leg_2", f"{hedge_legs[1]['leg']} {hedge_legs[1]['lots']} lots"),
    ]
    
    # Write CSV
    with filepath.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["field", "value"])
        writer.writerows(rows)
    
    return filepath


def save_stress_csv(stress_rows: List[Dict[str, Any]], *, prefix: str = "stress_pack") -> Path:
    """
    Save stress test results as CSV with one row per scenario.
    
    Args:
        stress_rows: List of stress test scenarios with results
        prefix: Filename prefix (default: "stress_pack")
    
    Returns:
        Path to saved CSV file
    """
    REPORTS_DIR.mkdir(exist_ok=True)
    filepath = REPORTS_DIR / f"{prefix}_{_timestamp()}.csv"
    
    # Handle empty results
    if not stress_rows:
        filepath.write_text("")
        return filepath
    
    # Write all scenarios
    columns = list(stress_rows[0].keys())
    with filepath.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(stress_rows)
    
    return filepath
